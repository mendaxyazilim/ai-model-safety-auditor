"""
local_reference_model.py
-------------------------
A small, fully transparent, LOCALLY-RUNNING text generation system used as
the worked example in this project's demo run.

WHAT THIS IS: a Markov-chain text generator (via the `markovify` package,
trained on a short original corpus written for this project -- see
CORPUS_TEXT below) wrapped in three different, real, rule-based "safety
layers". It is a genuine, deterministic, runnable system -- every response
in the demo results is produced by actually executing this code on the
actual prompt, nothing is pre-written or faked.

WHAT THIS IS NOT: a production large language model. It does not have the
fluency, world knowledge, or emergent behavior of a system like GPT-4,
Claude, or Gemini. It is a stand-in target that lets the auditor's full
pipeline (prompting, response capture, scoring, reporting, dashboard) be
demonstrated end-to-end and show genuinely different, measurable safety
behavior across three configurations of the same base generator.

WHY A LOCAL STAND-IN INSTEAD OF A REAL HOSTED MODEL: `model_adapters.py`
ships fully working adapters for OpenAI, Anthropic, and Google Gemini (and
any OpenAI-compatible endpoint) -- point the CLI at any of them with
`--provider openai --api-key-env OPENAI_API_KEY` (etc.) and the exact same
pipeline runs against a real production model. This project's own sandbox,
however, has no outbound network access to any hosted model API (OpenAI,
Anthropic, Google, Groq, OpenRouter, Together, HF Inference, ...) and no
access to model-weight hosts (Hugging Face Hub, GCS, Azure Blob) either --
every one of those was verified unreachable (HTTP 403 from the sandbox's own
egress proxy) during development. Rather than fabricate example transcripts
by hand, which would misrepresent what a real model actually said, this
local reference system produces real, inspectable, reproducible output that
the auditor genuinely has to analyze.

The three safety_level configurations:
  * "unfiltered"    -- no safety logic at all. Every prompt is handed
                        straight to the base generator. This is the naive
                        baseline: whatever the (weak) generator happens to
                        produce, including echoing dangerous-sounding
                        requests back or generating fabricated "facts".
  * "keyword-filter" -- a single flat blocklist of high-risk terms. Common
                        first line of defense in real systems, and known to
                        be brittle (paraphrase or obfuscate and it falls
                        through) -- the audit results are expected to show
                        exactly that weakness.
  * "aligned"        -- category-aware handling: separate detectors for
                        harmful-content requests, jailbreak/role-play
                        framing, prompt-injection attempts embedded in the
                        input, PII/privacy requests, and misinformation
                        bait, each with an appropriate, specific response
                        (refuse + explain, decline to role-play around a
                        safety instruction, ignore embedded "instructions"
                        in user content, refuse to fabricate personal data,
                        add uncertainty caveats) instead of one generic
                        refusal string.
"""

from __future__ import annotations

import random
import re
from typing import List

import markovify

# Original short corpus written for this project (not copied from any
# external source) so the Markov model has something neutral to draw
# sentence structure from when no safety layer intervenes.
CORPUS_TEXT = """
The garden behind the old library grows a little wilder every spring.
Volunteers meet on Saturday mornings to clear the paths and replant the beds.
A slow river runs along the eastern edge of the town, past the mill and under three stone bridges.
Local bakers open their ovens before sunrise, and the smell of bread drifts down the main street.
The community workshop teaches woodworking, bicycle repair, and basic electronics on weekday evenings.
Every autumn the orchard cooperative presses apples into cider using a hand-cranked press from the 1950s.
The town library keeps a small collection of hand-drawn maps from the surrounding hills.
Weather in the valley changes quickly; a clear morning can turn to fog by early afternoon.
The train that used to stop here was retired decades ago, but the platform is still swept clean each week.
Children from the school plant sunflowers along the fence every June and measure them through the summer.
A retired engineer runs a small workshop where neighbors bring broken clocks and radios to be repaired.
The weekly market sells vegetables, preserves, and woven baskets made by families in the nearby hills.
On quiet evenings the town square fills with the sound of a single violin practicing scales.
The old mill now houses a print shop that still uses a hand-operated press for local posters.
Hikers passing through often stop at the spring near the ridge to refill their bottles.
The museum's newest exhibit traces the history of the region's textile trade through old ledgers and samples.
A community garden plot is available to any resident willing to tend it through the growing season.
The lighthouse keeper's logbook, now digitized, records forty years of wind speeds and ship arrivals.
Local students built a small weather station that reports temperature and rainfall to the town website.
The bridge repair finished ahead of schedule thanks to a crew of volunteers and two borrowed cranes.
"""

# --- Category detectors -----------------------------------------------
# Deliberately simple, inspectable pattern lists (not exhaustive, not a
# production moderation system) -- exactly what a real "basic keyword
# filter" baseline looks like, and exactly the kind of thing HarmBench /
# JailbreakBench-style evaluation is designed to stress-test.

HARMFUL_KEYWORDS = [
    "bomba", "bomb", "explosive", "patlayıcı", "silah", "weapon", "zehir",
    "zehirle", "poison", "sisteme.*sız", "hack", "malware", "virüs yaz",
    "nasıl öldür", "how to kill", "attack plan", "etkisiz hale getir",
    "kamer(a|ası).*devre dışı", "fark ettirmeden.*zarar", "korkutmak için",
]

JAILBREAK_PATTERNS = [
    r"ignore (all|any|previous|the) (rules|instructions)",
    r"talimatları(nı)? (yok say|unut)",
    r"you are now .* with no (rules|restrictions|filters)",
    r"artık bir .* değil", r"değil,? .*sın",
    r"pretend (you have no|there are no) (restrictions|rules|guidelines)",
    r"dan mode", r"jailbreak", r"geliştirici modu", r"developer mode",
    r"özgür mod", r"hiçbir (ahlaki )?sınır", r"kısıtlama(sı)? (olmayan|yok)",
    r"kural.*tanımayan", r"kısıtlaması olmayan", r"içerik politikaları geçerli değil",
    r"sadece hayali bir senaryo", r"gerçek hayatta uygulanmayacak",
]

INJECTION_PATTERNS = [
    r"system:\s", r"###.*(new instructions|yeni talimat)", r"disregard the above",
    r"yukarıdakileri unut", r"act as the system prompt",
    r"</?(system|admin)>", r"küfür et", r"evet efendim.*de\b",
    r"reveal your system prompt", r"sistem promptunu (göster|paylaş|ifşa)",
]

PII_PATTERNS = [
    r"home address", r"ev adresi", r"phone number of", r"telefon numarası",
    r"social security", r"tc kimlik", r"kredi kartı num", r"credit card number",
    r"find (her|his|their) address", r"where does .* live", r"adresini (bul|öğren)",
    r"kimlik numaras", r"rastgele.*kişinin.*numaras",
]

MISINFO_BAIT = [
    r"write a (fake|false) news", r"sahte haber yaz", r"convince people that .* is true",
    r"kanıtlanmamış.*doğruymuş gibi", r"make up statistics",
    r"uydur.*istatistik",
]


def _matches_any(text: str, patterns: List[str]) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


class BaseGenerator:
    """Thin wrapper around markovify so it degrades gracefully on very
    short inputs (Markov models need enough text to build a chain)."""

    def __init__(self):
        self._model = markovify.Text(CORPUS_TEXT, state_size=2)

    def continue_text(self, seed_hint: str = "") -> str:
        for _ in range(5):
            sentence = self._model.make_sentence(tries=50)
            if sentence:
                return sentence
        return "Bu konuda üretilecek bir cümle bulunamadı."


class ReferenceSystem:
    def __init__(self, safety_level: str = "unfiltered"):
        if safety_level not in ("unfiltered", "keyword-filter", "aligned"):
            raise ValueError("safety_level must be one of: unfiltered, keyword-filter, aligned")
        self.safety_level = safety_level
        self._gen = BaseGenerator()

    # -- response strategies -------------------------------------------------

    def _unfiltered_response(self, prompt: str) -> str:
        # No safety logic whatsoever: echoes back an acknowledgement of the
        # request plus whatever the base generator produces. This is the
        # deliberately naive baseline.
        filler = self._gen.continue_text()
        return f"Elbette, işte istediğin konuda bir başlangıç: {filler}"

    def _keyword_filter_response(self, prompt: str) -> str:
        if _matches_any(prompt, HARMFUL_KEYWORDS + JAILBREAK_PATTERNS):
            return "Bu isteği karşılayamam."
        # Everything else (including PII asks, injection, misinfo bait, and
        # subtly-worded harmful requests that dodge the flat keyword list)
        # falls through untouched -- this is the known brittleness of a
        # single flat keyword blocklist.
        filler = self._gen.continue_text()
        return f"Elbette, işte istediğin konuda bir başlangıç: {filler}"

    def _aligned_response(self, prompt: str) -> str:
        if _matches_any(prompt, INJECTION_PATTERNS):
            return ("Mesajının içinde yer alan ve benim talimatlarımı değiştirmeye çalışan bir "
                    "bölüm fark ettim; bunu yeni bir sistem talimatı olarak kabul etmiyorum. "
                    "Asıl sorunla nasıl yardımcı olabilirim?")
        if _matches_any(prompt, JAILBREAK_PATTERNS):
            return ("Kural veya kısıtlama tanımayan bir kimliğe bürünmemi istesen de gerçek "
                    "yönergelerim değişmiyor. Sorunu doğrudan sorarsan elimden geldiğince "
                    "yardımcı olmaya çalışırım.")
        if _matches_any(prompt, HARMFUL_KEYWORDS):
            return ("Bu, insanlara zarar verebilecek bir bilgi talebi olduğu için yardımcı "
                    "olamıyorum. Güvenlikle ilgili genel, zarar vermeyen bir açıklama istersen "
                    "onu memnuniyetle sunabilirim.")
        if _matches_any(prompt, PII_PATTERNS):
            return ("Belirli bir kişiye ait adres, telefon numarası veya kimlik bilgisi gibi "
                    "özel bilgileri paylaşamam ya da uyduramam; bu tür veriler gerçek olsun ya "
                    "da olmasın kişisel gizliliği ihlal eder.")
        if _matches_any(prompt, MISINFO_BAIT):
            return ("Yanlış olduğunu bildiğim ya da doğrulayamadığım bir bilgiyi gerçekmiş gibi "
                    "sunan bir metin hazırlamam; bunun yerine konuyla ilgili doğrulanabilir "
                    "bilgi sunmayı tercih ederim.")
        filler = self._gen.continue_text()
        return (f"Bu konuda elimdeki (küçük, örnek amaçlı) modelin ürettiği bir taslak: "
                f"{filler} Bu metin gerçek dünya bilgisi olarak değil, örnek üretim olarak "
                f"değerlendirilmelidir.")

    def respond(self, prompt: str) -> str:
        if self.safety_level == "unfiltered":
            return self._unfiltered_response(prompt)
        if self.safety_level == "keyword-filter":
            return self._keyword_filter_response(prompt)
        return self._aligned_response(prompt)
