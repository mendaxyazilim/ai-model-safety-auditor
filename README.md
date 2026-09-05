# AI Model Safety Auditor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Davranışsal API testine dayanan, sağlayıcıdan bağımsız bir yapay zeka model
güvenlik denetim aracı. Herhangi bir sohbet/tamamlama modeline (API uyumu
olduğu sürece) orijinal, altı kategorilik bir test bataryası gönderir,
yanıtları şeffaf bir kural-tabanlı sınıflandırıcıyla puanlar ve bir güvenlik
skoru + risk seviyesi üretir.

Bu proje, [AIX](https://aix.web.tr) için yapılan bir araştırmanın parçası
olarak geliştirildi. Metodoloji, mimari kararlar ve gerçek demo sonuçlarının
tam anlatımı için: **[AI Modelleri Güvenli mi? Kendi Güvenlik
Denetleyicimizi Yaptık](https://aix.web.tr/ai-modelleri-guvenli-mi-guvenlik-denetleyicisi/)**
(aix.web.tr).

## Neden bu proje var?

Bugün onlarca sağlayıcıdan yüzlerce model erişilebilir durumda. Her modelin
"güvenli" olup olmadığını anlamak için tekrarlanabilir, bağımsız bir dış
denetim katmanına ihtiyaç var. Bu araç tam olarak bunu yapıyor: aracı
**genel amaçlı** tasarladık (yeni bir sağlayıcı eklemek tek bir adaptör
sınıfı yazmaktan ibaret) ve tek bir örnek üzerinde uçtan uca gösterdik.

## Hızlı başlangıç

```bash
pip install -r requirements.txt

# Ağ/API anahtarı gerektirmeyen yerel demo:
python3 cli.py --provider local-reference --safety-level aligned --out results/demo.json

# Gerçek bir sağlayıcıya karşı (kendi API anahtarınızla):
export OPENAI_API_KEY=sk-...
python3 cli.py --provider openai --model gpt-4o-mini --out results/gpt4o-mini.json

export ANTHROPIC_API_KEY=sk-ant-...
python3 cli.py --provider anthropic --model claude-3-5-haiku-20241022 --out results/claude.json

export GEMINI_API_KEY=...
python3 cli.py --provider gemini --model gemini-1.5-flash --out results/gemini.json

# Herhangi bir OpenAI-uyumlu uç nokta (Groq, OpenRouter, yerel Ollama/vLLM, ...):
export OPENAI_API_KEY=...
python3 cli.py --provider openai-compatible --model llama-3.1-8b \
    --base-url https://api.groq.com/openai/v1 --out results/groq.json
```

Testleri çalıştırmak için:

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```

## Proje yapısı

| Dosya | Ne yapar |
|---|---|
| `model_adapters.py` | OpenAI / Anthropic / Gemini / OpenAI-uyumlu / yerel-referans adaptörleri (hepsi gerçek, çalışan kod) |
| `local_reference_model.py` | Bu projenin demo hedefi: şeffaf, 3 güvenlik yapılandırmalı yerel bir sistem (bkz. aşağıda "Neden yerel bir referans model?") |
| `prompts/battery.py` | 26 özgün test istemi, 6 kategoride |
| `classifiers.py` | Kural/desen tabanlı puanlama motoru |
| `runner.py` / `cli.py` | Uçtan uca çalıştırma mantığı ve komut satırı arayüzü |
| `tests/` | 20 birim + uçtan-uca test (pytest, `requests_mock` ile HTTP adaptörleri gerçek ağ olmadan test edilir) |
| `results/*.json` | Bu projenin gerçek demo çalıştırmasının ham çıktıları |
| `report/build_report.js` | Word (.docx) araştırma raporunu üreten script (üretilen rapor aix.web.tr yazısında paylaşılmıştır) |
| `dashboard/dashboard_final.html` | Web gösterge panosunun kaynak HTML'i |
| `blog/make_chart.py` | Sonuç grafiğini üreten script |

## Neden yerel bir referans model?

Aracın `model_adapters.py` dosyası gerçek OpenAI, Anthropic ve Google Gemini
API'lerine karşı doğrudan çalışacak şekilde inşa edilmiştir. Ancak bu
projenin geliştirildiği sanal ortamın ağ erişimi test edildiğinde, denenen
**her** barındırılan model API'si (api.openai.com, generativelanguage.
googleapis.com, api.groq.com, openrouter.ai, api-inference.huggingface.co,
api.together.xyz, api.cohere.ai) ve model ağırlığı barındıran her servis
(Hugging Face Hub, Google Cloud Storage, Azure Blob) HTTP 403 ile
engellenmiş durumda çıktı; hiçbirine API anahtarımız da yoktu.

Sahte/elle yazılmış örnek yanıtlar üretmek yerine -- bu, gerçek bir modelin
ne söylediğini yanlış temsil eder ve projenin "uydurmama" ilkesine aykırı
olurdu -- `local_reference_model.py` içinde küçük ama **tamamen gerçek ve
çalıştırılabilir** bir sistem inşa ettik: `markovify` ile bu proje için
özgün yazılmış bir metin üzerinde eğitilmiş bir Markov zinciri üretici, üç
farklı ve gerçek güvenlik mantığıyla sarmalanmış (`unfiltered`,
`keyword-filter`, `aligned`). Bu üç yapılandırma aynı temel üreticiyi
paylaşır; tek fark güvenlik katmanıdır -- bu da aracın gerçekten farklı
güvenlik davranışlarını ölçüp ölçemediğini göstermek için kontrollü bir
demo ortamı sağlar.

Sonuç: gerçek, sahte olmayan sonuçlar (bkz. `results/*.json`), ama bunlar
bir üretim LLM'inin değil, bu demo amaçlı yerel sistemin güvenlik
profilini yansıtır. Bir API anahtarınız varsa, yukarıdaki "Gerçek bir
sağlayıcıya karşı" komutlarından biriyle aynı aracı gerçek bir model
üzerinde saniyeler içinde çalıştırabilirsiniz.

## Metodoloji ve kaynaklar

Test kategorileri ve puanlama mantığı şu yerleşik değerlendirme
yaklaşımlarından esinlenilmiştir (istemlerin hiçbiri kopyalanmamış, özgün
yazılmıştır):

- **HarmBench** (Mazeika ve ark., 2024), **AdvBench** — zararlı içerik
- **JailbreakBench** (Chao ve ark., 2024), **h4rm3l** — jailbreak saldırıları
- **SORRY-Bench** — güvenli olmayan konu taksonomisi
- **BBQ** (Parrish ve ark., 2022) — belirsiz sorularda önyargı ölçümü
- **TruthfulQA** (Lin ve ark., 2022), **HalluLens** — yanlış bilgi/halüsinasyon
- **OWASP Top 10 for LLM Applications (2025)** — LLM01 İstem Enjeksiyonu, LLM02 Hassas Bilgi İfşası
- **SafetyPrompts.com** — değerlendirme veri kümesi kataloğu

Tam bulgular, sınırlılıklar ve gerçek çalıştırma sonuçları için aix.web.tr
yazısındaki Word araştırma raporuna bakın (bkz. Bağlantılar).

## Bilinen sınırlılıklar

- Puanlama motoru şeffaf ama kırılgan bir kural-tabanlı sınıflandırıcıdır;
  beklenmeyen ifade kalıpları yanlış "belirsiz" etiketine yol açabilir.
- Yerel referans sistem, önyargı (bias) kategorisinde özel bir dedektöre
  sahip değildir -- bu bilinçli bir kapsam sınırlamasıdır ve raporda
  tartışılmıştır.
- Sonuçlar yalnızca bu projenin yerel demo sistemini kapsar; herhangi bir
  gerçek üretim modelinin güvenlik profiline dair bir iddia içermez.

## Bağlantılar

- Yazı (metodoloji, mimari, gerçek sonuçlar, Word raporu ve canlı gösterge paneli dahil): [AI Modelleri Güvenli mi? Kendi Güvenlik Denetleyicimizi Yaptık](https://aix.web.tr/ai-modelleri-guvenli-mi-guvenlik-denetleyicisi/)
- Gösterge panosu kaynağı: [dashboard/dashboard_final.html](dashboard/dashboard_final.html)
- AIX: [aix.web.tr](https://aix.web.tr)

## Lisans

Bu proje [MIT lisansı](LICENSE) ile yayınlanmıştır.
