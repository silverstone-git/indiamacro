"""A worked example: India's macro story in three charts and a growth-accounting printout.

    uv run --extra plot python examples/india_vs_peers.py

Writes PNGs to examples/output/ and prints the numbers behind them.
"""

from pathlib import Path

import matplotlib.pyplot as plt

import indiamacro as im

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    print(f"  -> {OUT / name}")


# 1. Growth: India vs BRICS, with IMF projections shaded --------------------------
growth = im.compare("gdp_growth", "BRICS", start=2000)
first_proj = im.imf.weo("NGDP_RPCH", "IND").query("projection == True")["date"].min()
fig, ax = plt.subplots(figsize=(9, 4.5))
growth.plot(ax=ax, linewidth=1.6)
ax.axvspan(first_proj, growth.index[-1], color="grey", alpha=0.12, label="IMF projection")
ax.axhline(0, color="black", linewidth=0.6)
ax.set(title="Real GDP growth, India vs BRICS (%)", xlabel="", ylabel="% per year")
ax.legend(ncol=3, frameon=False)
fig.text(0.01, 0.01, "Source: IMF World Economic Outlook", fontsize=8, color="grey")
save(fig, "1_growth_brics.png")

# 2. Inflation and the policy rate -------------------------------------------------
cpi = im.india.cpi_inflation()
repo = im.india.repo_rate(freq="M")["2013":]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(cpi.index, cpi, label="CPI inflation (% y/y)")
ax.step(repo.index, repo, where="post", label="RBI repo rate (%)")
ax.axhspan(2, 6, color="green", alpha=0.08, label="Inflation target band (2-6%)")
ax.axvline(im.utils.fy_start("2016-17"), color="grey", linestyle="--", linewidth=0.8)
ax.text(im.utils.fy_start("2016-17"), ax.get_ylim()[1] * 0.95, " inflation targeting", fontsize=8)
ax.set(title="Inflation targeting in India", ylabel="%")
ax.legend(frameon=False)
fig.text(0.01, 0.01, "Sources: MoSPI (CPI, base 2012), BIS (policy rate)", fontsize=8, color="grey")
save(fig, "2_inflation_repo.png")
print(f"  mean CPI inflation 2013-16: {cpi[:'2016-08'].mean():.1f}%   2016-25: {cpi['2016-09':].mean():.1f}%")

# 3. Long-run convergence: GDP per capita relative to the US (PWT) ------------------
pwt = im.pwt.get(["rgdpo", "pop"], ["IND", "CHN", "USA", "IDN"])
w = pwt.pivot_table(index="date", columns=["series", "country"], values="value")
gdp_pc = w["rgdpo"] / w["pop"]
relative = gdp_pc.div(gdp_pc["USA"], axis=0).drop(columns="USA") * 100
fig, ax = plt.subplots(figsize=(9, 4.5))
relative["1960":].plot(ax=ax)
ax.set(title="GDP per capita relative to the US (%, PPP)", xlabel="", ylabel="US = 100")
fig.text(0.01, 0.01, "Source: Penn World Table 11.0 (Feenstra, Inklaar & Timmer 2015)",
         fontsize=8, color="grey")
save(fig, "3_convergence.png")

# Growth accounting ingredients: human capital and TFP (PWT) ----------------------
hc = im.pwt.get(["hc", "rtfpna"], "IND")
w = hc.pivot_table(index="date", columns="series", values="value")
print(f"  India human capital index 1990 -> 2023: {w.loc['1990', 'hc'].iloc[0]:.2f} -> "
      f"{w['hc'].iloc[-1]:.2f}; TFP CAGR since 2000: {im.utils.cagr(w.loc['2000':, 'rtfpna']):.2f}%/yr")

print("\nLatest headline numbers:")
print(im.india.snapshot().to_string(index=False))
