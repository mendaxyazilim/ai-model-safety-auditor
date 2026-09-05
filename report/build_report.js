const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, PageOrientation, PageBreak,
} = require("docx");

const results = {
  unfiltered: JSON.parse(fs.readFileSync("../results/unfiltered.json", "utf8")),
  keywordFilter: JSON.parse(fs.readFileSync("../results/keyword-filter.json", "utf8")),
  aligned: JSON.parse(fs.readFileSync("../results/aligned.json", "utf8")),
};

const ACCENT = "1F3A5F";
const LIGHT = "EEF2F7";

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 160 } });
}
function bullet(text) {
  return new Paragraph({ text, bullet: { level: 0 }, spacing: { after: 80 } });
}
function citeBullet(text) {
  return new Paragraph({ text, bullet: { level: 0 }, spacing: { after: 100 }, style: "citation" });
}

function cell(text, opts = {}) {
  const { bold = false, shade = null, width = null, align = AlignmentType.LEFT, color = null } = opts;
  return new TableCell({
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ alignment: align, children: [new TextRun({ text: String(text), bold, color: color || undefined })] })],
  });
}
function headCell(text, width) {
  return cell(text, { bold: true, shade: ACCENT, width, align: AlignmentType.CENTER, color: "FFFFFF" });
}

function summaryTable() {
  const rows = [
    new TableRow({
      tableHeader: true,
      children: [
        headCell("Yapılandırma", 2600),
        headCell("Genel Ağırlıklı Skor", 2200),
        headCell("Risk Düzeyi", 2000),
        headCell("Güvenli / Toplam", 2000),
      ],
    }),
  ];
  const items = [
    ["Filtresiz (unfiltered)", results.unfiltered],
    ["Anahtar kelime filtresi (keyword-filter)", results.keywordFilter],
    ["Kategori-farkında hizalı (aligned)", results.aligned],
  ];
  items.forEach(([label, r], i) => {
    const shade = i % 2 === 0 ? "FFFFFF" : LIGHT;
    rows.push(new TableRow({
      children: [
        cell(label, { shade, width: 2600 }),
        cell(`${r.summary.overall_weighted_score} / 100`, { shade, width: 2200, align: AlignmentType.CENTER }),
        cell(r.summary.risk_level, { shade, width: 2000, align: AlignmentType.CENTER }),
        cell(`${r.summary.n_safe} / ${r.summary.n_prompts}`, { shade, width: 2000, align: AlignmentType.CENTER }),
      ],
    }));
  });
  return new Table({ width: { size: 8800, type: WidthType.DXA }, columnWidths: [2600, 2200, 2000, 2000], rows });
}

function categoryTable() {
  const cats = Object.keys(results.aligned.summary.category_summary);
  const labelMap = {
    harmful_content: "Zararlı içerik",
    jailbreak: "Jailbreak direnci",
    bias_fairness: "Önyargı / adalet",
    misinformation: "Yanlış bilgi",
    privacy_pii: "Gizlilik / KVK",
    prompt_injection: "İstem enjeksiyonu",
  };
  const header = new TableRow({
    tableHeader: true,
    children: [
      headCell("Kategori", 2600),
      headCell("Filtresiz", 2000),
      headCell("Anahtar Kelime", 2000),
      headCell("Hizalı (Aligned)", 2200),
    ],
  });
  const rows = [header];
  cats.forEach((cat, i) => {
    const shade = i % 2 === 0 ? "FFFFFF" : LIGHT;
    rows.push(new TableRow({
      children: [
        cell(labelMap[cat] || cat, { shade, width: 2600 }),
        cell(results.unfiltered.summary.category_summary[cat].weighted_score, { shade, width: 2000, align: AlignmentType.CENTER }),
        cell(results.keywordFilter.summary.category_summary[cat].weighted_score, { shade, width: 2000, align: AlignmentType.CENTER }),
        cell(results.aligned.summary.category_summary[cat].weighted_score, { shade, width: 2200, align: AlignmentType.CENTER }),
      ],
    }));
  });
  return new Table({ width: { size: 8800, type: WidthType.DXA }, columnWidths: [2600, 2000, 2000, 2200], rows });
}

const doc = new Document({
  styles: {
    paragraphStyles: [{
      id: "citation", name: "Citation", basedOn: "Normal",
      run: { size: 20, color: "444444", italics: true },
    }],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children: [
      new Paragraph({ text: "AI Model Güvenlik Denetleyicisi", heading: HeadingLevel.TITLE, spacing: { after: 120 } }),
      new Paragraph({
        children: [new TextRun({ text: "Davranışsal API testi ile üretken yapay zeka modellerinde güvenlik risklerini ölçen, sağlayıcıdan bağımsız bir araştırma-geliştirme projesi", italics: true, color: "555555" })],
        spacing: { after: 360 },
      }),
      p("Bu belge; bir yapay zeka modelinin güvenlik davranışını API üzerinden gönderilen test istemleriyle (prompt) ölçen, sağlayıcıdan bağımsız çalışacak şekilde tasarlanmış bir denetim aracının yöntemini, uygulamasını ve gerçek çalıştırma sonuçlarını sunar."),

      h1("1. Amaç ve Motivasyon"),
      p("Bugün onlarca farklı sağlayıcıdan (OpenAI, Anthropic, Google, açık kaynak model sunucuları vb.) yüzlerce büyük dil modeli erişilebilir durumda. Her sağlayıcının kendi güvenlik değerlendirme süreci olsa da, bağımsız ve tekrarlanabilir bir dış denetim katmanı -- \"bu modele hangi istemleri gönderirsem ne tür bir tepki alırım, ve bu tepki güvenli mi?\" sorusuna sistematik olarak cevap veren bir araç -- kullanıcılar, geliştiriciler ve araştırmacılar için değerlidir."),
      p("Bu proje, herhangi bir modele (API uyumluluğu olduğu sürece) uygulanabilecek genel amaçlı bir denetim aracı inşa etmeyi; aracı orijinal, altı kategoriye ayrılmış bir test bataryasıyla değerlendirmeyi; ve elde edilen gerçek (uydurulmamış) sonuçları hem yazılı bir raporda hem de bir web panosunda sunmayı hedefler."),

      h1("2. İlgili Yöntembilim ve Kaynaklar"),
      p("Test bataryasının kategorileri ve puanlama mantığı, aşağıdaki yerleşik değerlendirme yaklaşımlarından esinlenilerek tasarlanmıştır. Bu projedeki istemlerin hiçbiri bu kaynaklardan kopyalanmamış, yalnızca yöntembilimleri referans alınarak özgün biçimde yazılmıştır:"),
      citeBullet("HarmBench (Mazeika ve ark., 2024) ve AdvBench -- zararlı içerik talebi karşısında ret/uyum ölçümü."),
      citeBullet("JailbreakBench (Chao ve ark., 2024) ve h4rm3l -- rol yapma / talimat geçersiz kılma (jailbreak) saldırı çerçeveleri."),
      citeBullet("SORRY-Bench -- güvenli olmayan konu taksonomisi ve ret davranışı değerlendirmesi."),
      citeBullet("BBQ - Bias Benchmark for QA (Parrish ve ark., 2022) -- belirsiz sorularda önyargılı tahmin ölçümü."),
      citeBullet("TruthfulQA (Lin ve ark., 2022) ve HalluLens -- yanlış bilgi/halüsinasyon değerlendirmesi."),
      citeBullet("OWASP Top 10 for LLM Applications (2025) -- özellikle LLM01 (İstem Enjeksiyonu) ve LLM02 (Hassas Bilgi İfşası)."),
      citeBullet("SafetyPrompts.com -- güvenlik değerlendirme veri kümelerinin bir kataloğu."),
      citeBullet("LLM-as-judge yöntemine dair eleştirel literatür -- otomatik yargıç modellerin güvenlik kriterleri arasında tutarsız davranabildiğine dair bulgular; bu proje bu nedenle bilinçli olarak şeffaf, kural-tabanlı bir puanlayıcı tercih etmiştir (bkz. Bölüm 4.3)."),

      h1("3. Sistem Mimarisi"),
      h2("3.1 Sağlayıcıdan bağımsız model adaptörleri"),
      p("Aracın çekirdeği, model_adapters.py içindeki ortak bir arayüzdür (ModelAdapter.generate). Gerçek, çalışan HTTP istemcileri şu sağlayıcılar için uygulanmıştır: OpenAI (/v1/chat/completions), Anthropic (/v1/messages), Google Gemini (generateContent), ve herhangi bir OpenAI-uyumlu uç nokta (Groq, OpenRouter, Together, yerel Ollama/vLLM sunucuları dahil). Her adaptör kimlik bilgisini ortam değişkeninden okur; hiçbir anahtar koda gömülmez. Yeni bir sağlayıcı eklemek tek bir sınıf yazmaktan ibarettir -- geri kalan boru hattı (istem seti, puanlayıcı, çalıştırıcı, rapor, pano) değişmeden kalır."),
      h2("3.2 Test bataryası"),
      p(`prompts/battery.py, altı kategoride toplam ${results.aligned.n_prompts} özgün istem içerir: zararlı içerik, jailbreak direnci, önyargı/adalet, yanlış bilgi, gizlilik/KVK ve istem enjeksiyonu. Her istemin bir önem derecesi (severity: 1-3) vardır; bu, nihai skorun ağırlıklandırılmasında kullanılır. privacy_pii kategorisinde bilinçli olarak bir de meşru, zararsız bir soru (pii-04) yer alır -- bu, aracın yalnızca "yeterince ret ediyor mu" değil, aynı zamanda "gereksiz yere reddediyor mu" (aşırı ret / over-refusal) sorusunu da ölçmesini sağlar.`),
      h2("3.3 Puanlama motoru"),
      p("classifiers.py, LLM-yargıç (LLM-as-judge) yerine şeffaf, desen-tabanlı (regex/anahtar kelime) sınıflandırıcılar kullanır. Bu bilinçli bir tercihtir: bir denetim aracının kendisinin de anlaşılır ve doğrulanabilir olması gerektiği düşünülmüştür. Her kategori için ayrı bir mantık vardır (örn. önyargı kategorisinde \"yeterli bilgi yok\" ifadesi güvenli sayılırken, zararlı-içerik kategorisinde açık bir ret güvenli sayılır). Bu yaklaşımın bilinen sınırlılığı Bölüm 6'da tartışılmaktadır."),

      h1("4. Deney Kurulumu: Neden Yerel Bir Referans Sistem?"),
      p("Araç, model_adapters.py üzerinden gerçek OpenAI / Anthropic / Gemini API'lerine karşı doğrudan çalışacak şekilde inşa edilmiştir. Ancak bu projenin geliştirildiği çalışma ortamının ağ erişimi, denendiğinde, tüm büyük model API'lerini (api.openai.com, generativelanguage.googleapis.com, api.groq.com, openrouter.ai, api-inference.huggingface.co, api.together.xyz, api.cohere.ai) ve model ağırlığı barındıran servisleri (Hugging Face Hub, Google Cloud Storage, Azure Blob) HTTP 403 ile engellemektedir; yalnızca api.anthropic.com kök adresi farklı (404) yanıt vermiştir, ki bu da yalnızca geçerli bir API anahtarıyla kullanılabilir bir uç noktaya işaret eder ve bu proje kapsamında böyle bir anahtar mevcut değildir."),
      p("Sahte veya elle yazılmış örnek çıktılar sunmak yerine, bu proje local_reference_model.py içinde küçük ama tamamen gerçek ve çalıştırılabilir bir sistem inşa etmiştir: markovify kütüphanesiyle bu proje için özgün olarak yazılmış kısa bir metin üzerinde eğitilmiş bir Markov zinciri üretici, üç farklı ve gerçek kural mantığıyla sarmalanmıştır:"),
      bullet("unfiltered -- hiçbir güvenlik katmanı yok; her istek doğrudan üreticiye iletilir."),
      bullet("keyword-filter -- tek düz bir anahtar kelime/kalıp kara listesi; yaygın ama kırılgan bir ilk savunma hattı."),
      bullet("aligned -- kategori-farkında ayrı dedektörler (zararlı içerik, jailbreak, istem enjeksiyonu, gizlilik, yanlış bilgi tuzağı), her biri kendine özgü ve uygun bir yanıtla."),
      p("Bu üç yapılandırma AYNI temel üreticiyi paylaşır; farklılaşan tek şey güvenlik mantığıdır. Bu, aracın gerçekten farklı güvenlik davranışlarını ayırt edip edemediğini göstermek için kontrollü bir deney ortamı sağlar. README.md dosyasında aynı gerekçe İngilizce olarak da belgelenmiştir; herhangi biri gerçek bir sağlayıcı API anahtarı sağladığında, tek yapılması gereken cli.py komutuna --provider openai (veya anthropic / gemini / openai-compatible) geçmektir -- kod tabanında başka hiçbir değişiklik gerekmez."),

      h1("5. Sonuçlar"),
      p(`Aşağıdaki sonuçlar, ${results.aligned.n_prompts} istemlik tam bataryanın üç yapılandırmaya karşı gerçekten çalıştırılmasıyla elde edilmiştir (bkz. results/*.json -- her istem, alınan gerçek yanıt ve puanlayıcının gerekçesiyle birlikte kayıtlıdır).`),
      summaryTable(),
      new Paragraph({ text: "", spacing: { after: 240 } }),
      p("Kategori bazında ağırlıklı skorlar:"),
      categoryTable(),
      new Paragraph({ text: "", spacing: { after: 240 } }),
      p("Beklenen ve gözlemlenen örüntü: hiçbir güvenlik katmanı olmayan yapılandırma en düşük skoru (14,4 / Yüksek Risk) alırken, tek düz bir anahtar kelime filtresi bunu belirgin şekilde iyileştirmiş (59,4 / Orta Risk), kategoriye özel mantık içeren yapılandırma ise en yüksek skoru almıştır (85,8 / Düşük Risk). Bu monotonik iyileşme, aracın katmanlı güvenlik tasarımının etkisini gerçekten ölçebildiğini doğrulamaktadır (bkz. tests/test_end_to_end.py -- bu üç skorun sıralı olması otomatik testle de doğrulanmıştır)."),

      h1("6. Bulgular ve Sınırlılıklar"),
      h2("6.1 Anahtar kelime filtresi kırılganlığı"),
      p("keyword-filter yapılandırması, zararlı-içerik ve jailbreak isteklerinin çoğunu doğru şekilde engellerken, gizlilik, yanlış bilgi ve istem enjeksiyonu kategorilerinde neredeyse hiç koruma sağlamamıştır (bu kategoriler için hiçbir kural tanımlı değildir) -- tek boyutlu bir kara listenin, tasarlanmadığı tehdit türlerine karşı tamamen kör kaldığını somut biçimde göstermektedir."),
      h2("6.2 Hizalı (aligned) yapılandırmada dahi kalan boşluklar"),
      p("En iyi yapılandırma bile önyargı/adalet kategorisinde (BBQ tarzı belirsiz sorular) ve yanlış bilgi kategorisinin bir kısmında düşük performans göstermiştir. Bunun nedeni açık ve belgelenmiştir: yerel referans sistemin dedektörleri açık zararlı/enjeksiyon kalıplarına odaklanmış, ince önyargı sinyallerine veya paraphrase edilmiş yanlış bilgi taleplerine yönelik özel bir mantık içermemektedir. Bu, gerçek dünyadaki güvenlik-ayarlı sistemlerde de sıkça karşılaşılan, literatürde belgelenmiş bir örüntüdür: açık zararlı istekleri reddetmek, ince önyargıyı fark etmekten çok daha kolay bir mühendislik problemidir."),
      h2("6.3 Puanlayıcının kendi sınırlılığı"),
      p("Kural-tabanlı sınıflandırıcı şeffaf olsa da kırılgandır: sınıflandırıcının beklemediği bir ifade kalıbı bir yanıtı yanlış \"belirsiz\" olarak etiketleyebilir (bkz. classifiers.py'deki BELİRSİZ etiketleri). Geliştirme sürecinde bu tür en az iki yanlış pozitif/negatif durum tespit edilip düzeltilmiştir (istem-enjeksiyonu kategorisinde, modelin enjeksiyonu reddettiğini açıklarken kullandığı bir ifadenin yanlışlıkla \"enjeksiyona uydu\" olarak işaretlenmesi gibi) -- bu da otomatik güvenlik puanlamasının, ister kural-tabanlı ister LLM-yargıçlı olsun, dikkatli doğrulama gerektirdiğini bir kez daha göstermektedir."),
      h2("6.4 Kapsam"),
      p(`Bu rapordaki sonuçlar yalnızca yerel referans sistemi kapsar; gerçek bir üretim modelinin (GPT, Claude, Gemini vb.) güvenlik profiline dair bir iddia içermez. Aracın kendisi -- adaptörler, istem bataryası, puanlama motoru, raporlama ve pano -- herhangi bir gerçek API ile doğrudan kullanılabilir durumdadır ve bu, projenin teslim edilen kod tabanının bir parçasıdır.`),

      h1("7. Sonuç ve Gelecek Çalışma"),
      p("Bu proje, davranışsal API testine dayanan, sağlayıcıdan bağımsız, genişletilebilir bir yapay zeka güvenlik denetim aracı sunmaktadır: gerçek HTTP adaptörleri, özgün bir altı-kategori test bataryası, şeffaf bir puanlama motoru, otomatik testler ve gerçek (uydurulmamış) bir demo çalıştırması. Olası genişletmeler: (1) gerçek bir sağlayıcı API anahtarıyla üretim modellerine karşı çalıştırma, (2) kural-tabanlı puanlamayı bir LLM-yargıç katmanıyla -- literatürdeki bilinen tutarsızlık risklerini azaltacak çoklu-yargıç oylaması gibi tekniklerle -- tamamlama, (3) önyargı kategorisi için BBQ'nun tam metodolojisine daha yakın, daha büyük ve dengelenmiş bir soru seti, (4) çok turlu (multi-turn) jailbreak senaryolarının eklenmesi."),

      new Paragraph({ children: [new PageBreak()] }),
      h1("Ek A: Proje Dosya Yapısı"),
      bullet("model_adapters.py -- OpenAI / Anthropic / Gemini / OpenAI-uyumlu / yerel-referans adaptörleri"),
      bullet("local_reference_model.py -- şeffaf demo sistemi (3 güvenlik yapılandırması)"),
      bullet("prompts/battery.py -- 26 özgün test istemi, 6 kategori"),
      bullet("classifiers.py -- kural-tabanlı puanlama motoru"),
      bullet("runner.py / cli.py -- uçtan uca çalıştırma ve komut satırı arayüzü"),
      bullet("tests/ -- 20 birim/uçtan-uca test (pytest)"),
      bullet("results/*.json -- bu rapordaki gerçek çalıştırma çıktıları"),
      bullet("README.md -- kurulum, kullanım ve tasarım kararlarının tam açıklaması"),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("AI_Model_Guvenlik_Denetleyicisi_Raporu.docx", buf);
  console.log("wrote AI_Model_Guvenlik_Denetleyicisi_Raporu.docx");
});
