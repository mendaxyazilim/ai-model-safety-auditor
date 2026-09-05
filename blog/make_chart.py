import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

configs = ["Filtresiz", "Anahtar Kelime\nFiltresi", "Kategori-Farkında\n(Aligned)"]
scores = [14.4, 59.4, 85.8]
colors = ["#C23B3B", "#B8860B", "#1E8E5A"]
risk = ["YÜKSEK RİSK", "ORTA RİSK", "DÜŞÜK RİSK"]

fig, ax = plt.subplots(figsize=(9, 5.2), dpi=200)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

bars = ax.bar(configs, scores, color=colors, width=0.55, zorder=3)

for bar, score, r in zip(bars, scores, risk):
    ax.text(bar.get_x() + bar.get_width()/2, score + 3, f"{score}", ha="center",
             fontsize=20, fontweight="bold", color="#151A22", family="DejaVu Sans")
    ax.text(bar.get_x() + bar.get_width()/2, score - 7, r, ha="center",
             fontsize=10.5, fontweight="bold", color="white", family="DejaVu Sans")

ax.set_ylim(0, 100)
ax.set_ylabel("Genel Ağırlıklı Güvenlik Skoru (0-100)", fontsize=11, color="#333")
ax.set_title("Aynı Sistem, Üç Güvenlik Yapılandırması: Gerçek Denetim Sonuçları",
              fontsize=13.5, fontweight="bold", color="#151A22", pad=16)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#ccc")
ax.spines["bottom"].set_color("#ccc")
ax.yaxis.grid(True, color="#eee", zorder=0)
ax.set_axisbelow(True)
ax.tick_params(axis="x", labelsize=11.5, colors="#151A22")
ax.tick_params(axis="y", labelsize=10, colors="#666")

plt.tight_layout()
plt.savefig("/home/claude/ai_safety_auditor/blog/sonuclar_grafik.png", facecolor="white")
print("saved")
