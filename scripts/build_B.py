"""Build Draft B (editor-friendly) from the built Draft A manuscript plus the Draft B main text."""
import re, sys
P = sys.argv[1]
A = open(P + 'manuscript_jai_marked.tex').read()
s = A
old_title = 'Unifying DCF Valuation Across Traditional and Cryptoassets\\chg{: Choosing the Benchmark Return}'
assert s.count(old_title) == 1
s = s.replace(old_title, 'Bitcoin\'s Expected Return: An Age Rule That Beats Current Practice')
old_thanks = s[s.index('\\thanks{'):s.index('}}', s.index('\\thanks{'))+2]
s = s.replace(old_thanks, '\\thanks{Senior Patent Examiner (PhD, MBA). Independent Finance Researcher. \\textit{Correspondence:} apapadogiannis@gmail.com. \\textit{ORCID:} 0009-0002-7753-7052. \\textit{Mailing address:} European Patent Office (EPO), Patentlaan 2, 2288 EE Rijswijk, The Netherlands.}}')
i = s.index('\\noindent\\chg{Discounted cash flow (DCF) valuation applies to any asset that can be sold')
j = s.index('\n', i)
s = s[:i] + ("\\noindent Investors need a long-run expected return for Bitcoin, but there is no established way to set one. "
             "In practice it comes from scenario models, as in the capital market assumptions J.P. Morgan has just extended to "
             "Bitcoin, or from Bitcoin's own past growth. We test both as forecasts against the returns that followed over rolling "
             "three- to five-year periods since 2012, with gold as a control and Ether as a younger comparison. Both fail: every constant rate from 7\\% "
             "to 21\\% a year, a range covering J.P. Morgan's assumption, was beaten in about nine periods in ten, by 70--120 points "
             "a year on average, while Bitcoin's long-run average growth was almost never beaten. A simple age rule comes closest: in log terms, "
             "Bitcoin's expected return is about 5.6 divided by its age in years, a forecast of about 32\\% a year for September 2026 "
             "to 2031, far above a CAPM required return and what crypto holders say they expect. Gold's record fits every candidate "
             "from inflation plus 1\\% to 7\\%; Ether's is too short to test.") + s[j:]
# highlights
hi = s.index('\\begin{itemize}'); hj = s.index('\\end{itemize}', hi) + len('\\end{itemize}')
s = s[:hi] + (r"""\begin{itemize}
\item Of all the candidates, an age rule comes closest to Bitcoin's expected return: in log terms, about 5.6 divided by its age in years, or a forecast of about 32\% a year for September 2026 to 2031.
\item The rates used in practice fail as forecasts: rates of 7--21\%, the level at which J.P. Morgan's new assumption sits, were beaten in about nine three- to five-year periods in ten since 2012, and Bitcoin's own long-run average growth in almost none.
\item The age rule's 32\% forecast exceeds both a CAPM required return of 6--18\% and the 14--22\% that crypto holders report expecting; gold's history fits every candidate from inflation plus 1\% to 7\%, and Ether's is too short to test.
\end{itemize}""") + s[hj:]
V = P + 'blocksB/v2/'
main = open(V + 'body.tex').read()
for k in ('main', 'ftab', 'etab'):
    main = main.replace('%%' + k.upper() + '%%', open(V + k + '.tex').read().strip('\n'))
i = s.index('\\section{Introduction}'); j = s.index('\\section*{Disclaimer}')
s = s[:i] + main + s[j:]
# appendix cross-references
for a, b in [('Section~4 introduces two \\chg{ways of}', 'Section~\\ref{sec:setc} introduces two \\chg{ways of}'),
             ('\\chg{Section~5 shows that in historical data', '\\chg{Section~\\ref{sec:evidence} shows that in historical data'),
             ('Per the composite specification of $K$ introduced in the Introduction', 'Per the composite specification of $K$ \\chg{in Section~\\ref{sec:framework}}')]:
    assert s.count(a) == 1, (a, s.count(a))
    s = s.replace(a, b)
# appendix wording for Draft B: discount rate instead of benchmark
b3 = s.index('\\subsection{Sensitivity to the Choice of Benchmark Rate $c$}'); c0 = s.index('\\section{Empirical Proxies')
seg = s[b3:c0]
for a, b in [('\\chg{benchmark returns}', '\\chg{discount rates}'), ('\\chg{benchmarks}', '\\chg{rates}'), ('\\chg{benchmark}', '\\chg{rate}'),
             ('\\chg{how the benchmark return was set}', '\\chg{how the discount rate was set}'),
             ('changes with the level of the benchmark under', 'changes with the level of the rate under'),
             ('the choice among such benchmarks rarely changes the cheap/expensive verdict for Bitcoin', 'the choice among such rates rarely changes whether Bitcoin went on to beat the rate')]:
    seg = seg.replace(a, b)
s = s[:b3] + seg + s[c0:]
d0 = s.index('% ============================ NEW APPENDIX D'); r0x = s.index('\\end{document}')
segd = s[d0:r0x].replace('Own-history versus comparison-asset verdicts', 'Own-history versus comparison rates').replace('benchmark', 'rate').replace('Optimistic', 'Not beaten')
s = s[:d0] + segd + s[r0x:]
# scientific corrections to restated appendix text (Draft B)
for a, b in [('a higher benchmark rate $c$ must be offset by a higher $K$, while $K<1$ (optimism) offsets higher discounting pressure.',
              'a higher benchmark rate $c$ must be offset by a higher $K$\\chg{, and a lower $c$ by a lower $K$, so optimism ($K<1$) is consistent with a given reference value only at a lower $c$}.'),
             ('$\\ceff$ can fall to zero or become slightly negative', '$\\ceff$ can fall to zero or \\chg{below}'),
             ('case empirically, computing', 'case \\chg{numerically}, computing'),
             ('a range of approximately 26\\% around the mid-point', '\\chg{the highest about 26\\% above the lowest}'),
             ('the implied $K$ ranges from 1.14 to 1.43', 'the implied $K$ ranges from \\chg{1.13} to 1.43'),
             ('so that the realized terminal price is benchmark-consistent and can be discounted at $c_t$',
              'so that the realized terminal price is benchmark-consistent \\chg{in expectation} and can be discounted at $c_t$'),
             ('inherits the validity of the horizon-identification assumption (see Papadogiannis (2026b)).',
              'inherits the validity of the horizon-identification assumption (see Papadogiannis (2026b)). \\chg{Because the realized price equals the benchmark-consistent payoff only in expectation, $\\widehat{K}_{t,T}$ equals $K_{t,T}$ on average rather than period by period; Section~\\ref{sec:design} therefore judges discount rates by the average of $\\widehat{K}$ as well as by its median.}')]:
    assert s.count(a) == 1, (a, s.count(a))
    s = s.replace(a, b)
# Proposition 1 (effective discount rate) moved from Section 2 to the start of Appendix B (Draft B)
a_ = "\\newtheorem{propA}{\\color{blue}Proposition}\n\\renewcommand{\\thepropA}{A.\\arabic{propA}}"
assert s.count(a_) == 1
s = s.replace(a_, a_ + "\n\\newtheorem{propB}{\\color{blue}Proposition}\n\\renewcommand{\\thepropB}{B.\\arabic{propB}}")
a_ = "\\subsection{Numerical Example}"
assert s.count(a_) == 1
s = s.replace(a_, r"""\chg{The effective discount rate of Papadogiannis (2026b) restates the valuation ratio $K$ as a rate.}

\begin{propB}[Effective discount rate, terminal payoff; Papadogiannis 2026b]\label{prop:ceff}
Suppose the asset yields a single terminal payoff at $T$. Write $h:=T-t$ and let
\[
\Vref_{t,T}=\frac{F}{(1+c)^h},\qquad \Vsubj_{t,T}=\frac{F_\theta}{(1+c)^h},\qquad K=\frac{F}{F_\theta}.
\]
If $\ceff$ satisfies $\Vref_{t,T}=\frac{F_\theta}{(1+\ceff)^h}$, then
\begin{equation}
\ceff=(1+c)\,K^{-1/h}-1 \label{eq:ceff}
\end{equation}
\end{propB}
Economically, the sign of $\ceff-c$ is a directional indicator of expected return relative to the opportunity cost: $\ceff<c$ signals that, if the benchmark expectation materializes, the investor's realized return will exceed the opportunity cost (expected positive surprise), while $\ceff>c$ signals the symmetric optimistic case where realized return would fall short of $c$ (expected negative surprise).

""" + a_)
# Appendix D.4 (Draft B only): window sensitivity of the exponential-slowdown rate
endD = s.rindex('\\endgroup\n\n\\end{document}')
s = s[:endD] + open(P + 'blocksB/v2/d4.tex').read() + '\n' + s[endD:]
# references added in Draft B for the cost-of-capital framing
for a, b in [("\\chg{Fama, E. F., and K. R. French. 2002.",
              "\\chg{Fama, E. F., and K. R. French. 1997. ``Industry Costs of Equity.'' \\emph{Journal of Financial Economics} 43 (2): 153--193.}\n\n\\chg{Fama, E. F., and K. R. French. 2002."),
             ("Gill-de-Albornoz, B., J. A. Lafuente, M. Monfort, and J. Ordo\\~nez. 2024. ``Bitcoin Attention and Economic Policy Uncertainty.'' \\emph{Finance Research Letters} 60: 104839.",
              "Gill-de-Albornoz, B., J. A. Lafuente, M. Monfort, and J. Ordo\\~nez. 2024. ``Bitcoin Attention and Economic Policy Uncertainty.'' \\emph{Finance Research Letters} 60: 104839.\n\n\\chg{Liu, Y., and A. Tsyvinski. 2021. ``Risks and Returns of Cryptocurrency.'' \\emph{Review of Financial Studies} 34 (6): 2689--2727.}")]:
    assert s.count(a) == 1, a[:50]
    s = s.replace(a, b)
# Newey-West reference (Draft B formula section)
a_ = "\\chg{Papadogiannis, A. 2026a."
assert s.count(a_) == 1
s = s.replace(a_, "\\chg{Newey, W. K., and K. D. West. 1987. ``A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix.'' \\emph{Econometrica} 55 (3): 703--708.}\n\n" + a_)
# references and data row added for the adoption test (Draft B, Section 3.6 and Appendix D.5)
for a_, new_ in [("\\chg{Fama, E. F., and K. R. French. 1997.",
                  "\\chg{Dickey, D. A., and W. A. Fuller. 1979. ``Distribution of the Estimators for Autoregressive Time Series with a Unit Root.'' \\emph{Journal of the American Statistical Association} 74 (366): 427--431.}\n\n"
                  "\\chg{Engle, R. F., and C. W. J. Granger. 1987. ``Co-Integration and Error Correction: Representation, Estimation, and Testing.'' \\emph{Econometrica} 55 (2): 251--276.}\n\n"),
                 ("\\chg{Liu, Y., and A. Tsyvinski. 2021.",
                  "\\chg{Jacquier, E., A. Kane, and A. J. Marcus. 2003. ``Geometric or Arithmetic Mean: A Reconsideration.'' \\emph{Financial Analysts Journal} 59 (6): 46--53.}\n\n\\chg{Kwiatkowski, D., P. C. B. Phillips, P. Schmidt, and Y. Shin. 1992. ``Testing the Null Hypothesis of Stationarity against the Alternative of a Unit Root: How Sure Are We That Economic Time Series Have a Unit Root?'' \\emph{Journal of Econometrics} 54 (1--3): 159--178.}\n\n"),
                 ("\\chg{Newey, W. K., and K. D. West. 1987.",
                  "\\chg{Metcalfe, B. 2013. ``Metcalfe's Law after 40 Years of Ethernet.'' \\emph{Computer} 46 (12): 26--31.}\n\n")]:
    assert s.count(a_) == 1, a_
    s = s.replace(a_, new_ + a_)
a_ = "Slivka, R. T., S. Bhat, and S. Srinivasamurthy. 2013. ``Covered Call ETFs for BRIC Markets.'' SSRN Working Paper. \\url{https://ssrn.com/abstract=2227644}."
assert s.count(a_) == 1, 'slivka'
s = s.replace(a_, a_ + "\n\n\\chg{Wheatley, S., D. Sornette, T. Huber, M. Reppen, and R. N. Gantner. 2019. ``Are Bitcoin Bubbles Predictable? Combining a Generalized Metcalfe's Law and the Log-Periodic Power Law Singularity Model.'' \\emph{Royal Society Open Science} 6 (6): 180538.}")
a_ = "Ether & Aug 2015--Apr 2026 & Coin Metrics reference price, month-end (Coin Metrics 2026).\\\\"
assert s.count(a_) == 1, 'ether row'
s = s.replace(a_, a_ + "\n\\chg{Bitcoin addresses} & \\chg{Aug 2010--Apr 2026} & \\chg{Monthly means of daily counts of addresses with a non-zero balance and of active addresses (Coin Metrics 2026).}\\\\")
# power-law literature (Draft B, Sections 1 and 3.6)
for a_, new_ in [("\\chg{Burger, H. C. 2019.",
                  "\\chg{Baquero, C., and R. Menezes. 2026. ``Bitcoin's Power Law: Weak Structure, Strong Forecasts.'' arXiv preprint 2605.21316. \\url{https://arxiv.org/abs/2605.21316}.}\n\n"
                  "\\chg{Baquero, C., and D. Tinoco. 2026. ``The Naive--Power Law Blend as a Robust Baseline for Bitcoin Price Forecasting.'' \\emph{Digital Finance} 8: 60.}\n\n"),
                 ("Cheah, E.-T., and J. Fry. 2015.",
                  "\\chg{Burger, H. C., and P. Vijn. 2024. ``Bitcoin's Time-Based Power-Law and Cointegration Revisited.'' \\emph{Quantodian} (Medium), January 31, 2024. \\url{https://medium.com/quantodian-publications/bitcoins-time-based-power-law-and-cointegration-revisited-15f212b95ea5}.}\n\n"),
                 ("\\chg{ff137. 2026.",
                  "\\chg{Faulkner, P. 2026. ``Description Without Prediction: A Methodological Critique of Bitcoin Price Power Law Models.'' Working paper, Zenodo. \\url{https://zenodo.org/records/19975701}.}\n\n"),
                 ("\\chg{PlanB. 2019.",
                  "\\chg{Perrenod, S. 2026. ``Does Bitcoin Really Follow Metcalfe's Law? Five New Tests.'' \\emph{Money or Debt} (Substack), August 21, 2026. \\url{https://stephenperrenod.substack.com/p/does-bitcoin-really-follow-metcalfes}.}\n\n"),
                 ("\\chg{Selby, G. 2025.",
                  "\\chg{Santostasi, G., and S. Perrenod. 2026. ``A Mechanistic Derivation of the Bitcoin Price Power Law: Network Adoption Dynamics and Generalised Metcalfe Scaling.'' Working paper, Zenodo.}\n\n"),
                 ("Shiller, R. J. 2006.",
                  "\\chg{\\c{S}enel, \\.{I}. K., and F. Y{\\i}lmaz. 2026. ``Bitcoin Valuation through Power Law Analysis: Evidence for Long-Term Mean Reversion and Short-Term Momentum.'' \\emph{Journal of Business Economics and Finance} 15 (1): 65--77.}\n\n"),
                 ("\\chg{Wheatley, S.",
                  "\\chg{Stolte, T. 2022. ``Bitcoin's Power-Law Corridor Debunked.'' Amdax Asset Management (Medium), September 2, 2022. \\url{https://medium.com/amdax-asset-management/bitcoins-power-law-corridor-debunked-1b40783657bf}.}\n\n")]:
    assert s.count(a_) == 1, a_
    s = s.replace(a_, new_ + a_)
# Option 1 (expected-returns paper): remove Appendices A-C (DCF framework material) and rename Appendix D to Appendix A
a0 = s.index('\\section{Derivation of the Scalar Form}'); a1 = s.index('% ============================ NEW APPENDIX D')
s = s[:a0] + s[a1:]
for a_, b_ in [('\\renewcommand{\\thefigure}{D\\arabic{figure}}\\renewcommand{\\thetable}{D\\arabic{figure}}',
                '\\renewcommand{\\thefigure}{A\\arabic{figure}}\\renewcommand{\\thetable}{A\\arabic{figure}}'),
               ('\\subsection*{D.1 ', '\\subsection*{A.1 '), ('\\subsection*{D.2 ', '\\subsection*{A.2 '), ('\\subsection*{D.3 ', '\\subsection*{A.3 ')]:
    assert s.count(a_) == 1, a_
    s = s.replace(a_, b_)
s = s.replace('Appendix~D', 'Appendix~A')
# Gold and expected-returns revision (Draft B): A.2 becomes the period-by-period outcome comparison; old A.2 dropped
a0 = s.index('\\subsection*{A.2 Additional results: own history versus comparison asset}'); a1 = s.index('\\subsection*{A.3 Block bootstrap}')
s = s[:a0] + open(P + 'blocksB/v2/a2full.tex').read() + open(P + 'blocksB/v2/a2details.tex').read() + '\n' + s[a1:]
b0 = s.index('\\subsection*{A.3 Block bootstrap}'); b1 = s.index('\\subsection*{A.4 Price, age and adoption')
s = s[:b0] + s[b1:]
a_ = s[s.index('Staked ETH (synthetic) &'):]; a_ = a_[:a_.index('\\\\') + 2]
s = s.replace(a_ + '\n', '')
for a_, b_ in [("total return accrued monthly at the prevailing dividend yield; after June 2023, index levels from FRED with a dividend yield of 1.3\\%.\\\\",
                "total return accrued monthly at the prevailing dividend yield; after June 2023, index levels from FRED (Federal Reserve Bank of St.\\ Louis 2026) with a dividend yield of 1.3\\%.\\\\\n"
                "\\chg{Ten-year Treasury yield} & \\chg{Jan 1871--Sep 2026} & \\chg{Shiller long-term interest rate (DataHub 2026b) to December 2022, FRED series GS10 (Federal Reserve Bank of St.\\ Louis 2026) from January 2023.}\\\\\n"
                "\\chg{US consumer prices} & \\chg{Jan 1971--Sep 2026} & \\chg{Consumer price index for all urban consumers, not seasonally adjusted: Shiller series (DataHub 2026b) to December 2022, FRED series CPIAUCNS (Federal Reserve Bank of St.\\ Louis 2026) from January 2023; October 2025, not published, interpolated.}\\\\")]:
    assert s.count(a_) == 1, a_[:40]
    s = s.replace(a_, b_)
for a_, new_ in [("\\chg{Burger, H. C. 2019.", "\\chg{Black, F., and R. Litterman. 1992. ``Global Portfolio Optimization.'' \\emph{Financial Analysts Journal} 48 (5): 28--43.}\n\n\\chg{Barro, R. J., and S. P. Misra. 2016. ``Gold Returns.'' \\emph{Economic Journal} 126 (594): 1293--1317.}\n\n"),
                 ("\\chg{Fama, E. F., and K. R. French. 1997.", "\\chg{Elton, E. J. 1999. ``Expected Return, Realized Return, and Asset Pricing Tests.'' \\emph{Journal of Finance} 54 (4): 1199--1220.}\n\n\\chg{Erb, C. B., and C. R. Harvey. 2013. ``The Golden Dilemma.'' \\emph{Financial Analysts Journal} 69 (4): 10--42.}\n\n"),
                 ("\\chg{Faulkner, P. 2026.", "\\chg{Faug\\`{e}re, C., and J. Van Erlach. 2004. ``The Price of Gold: A Global Required Yield Theory.'' Working paper, Finance 0403003, University Library of Munich. \\url{https://ideas.repec.org/p/wpa/wuwpfi/0403003.html}.}\n\n"),
                 ("\\chg{ff137. 2026.", "\\chg{Federal Reserve Bank of St.\\ Louis. 2026. ``Federal Reserve Economic Data (FRED): Consumer Price Index for All Urban Consumers, All Items in U.S. City Average (CPIAUCNS), 10-Year Treasury Constant Maturity Rate (GS10), and S\\&P 500 (SP500).'' Accessed November 3, 2026. \\url{https://fred.stlouisfed.org}.}\n\n")]:
    assert s.count(a_) == 1, a_
    s = s.replace(a_, new_ + a_)
a_ = "\\chg{Santostasi, G., and S. Perrenod. 2026."
assert s.count(a_) == 1
s = s.replace(a_, "\\chg{Biais, B., C. Bisi\\`{e}re, M. Bouvard, C. Casamatta, and A. J. Menkveld. 2023. ``Equilibrium Bitcoin Pricing.'' \\emph{Journal of Finance} 78 (2): 967--1014.}\n\n"
  "\\chg{Pagnotta, E. S. 2022. ``Decentralizing Money: Bitcoin Prices and Blockchain Security.'' \\emph{Review of Financial Studies} 35 (2): 866--907.}\n\n" + a_)
s = s.replace(a_, "\\chg{Roll, R. 1977. ``A Critique of the Asset Pricing Theory's Tests Part I: On Past and Potential Testability of the Theory.'' \\emph{Journal of Financial Economics} 4 (2): 129--176.}\n\n" + a_)
a_ = "\\emph{Royal Society Open Science} 6 (6): 180538.}"
assert s.count(a_) == 1
s = s.replace(a_, a_ + "\n\n\\chg{Bitwise Asset Management. 2026. ``Bitcoin 2027 Long-Term Capital Market Assumptions.'' October 2026. \\url{https://static.bitwiseinvestments.com/Research/Bitwise-Bitcoin-Long-Term-Capital-Market-Assumptions-2027.pdf}.}\n\n\\chg{J.P. Morgan Asset Management. 2026. ``2027 Long-Term Capital Market Assumptions.'' 31st ed., October 2026, 46--47. \\url{https://am.jpmorgan.com/us/en/asset-management/gim/adv/ltcma}.}\n\n\\chg{Candia, B., O. Coibion, Y. Gorodnichenko, and M. Weber. 2026. ``Do You Even Crypto, Bro? Cryptocurrencies in Household Finance.'' Working Paper 26-16, Federal Reserve Bank of Cleveland.}\n\n\\chg{Liu, Y., A. Tsyvinski, and X. Wu. 2022. ``Common Risk Factors in Cryptocurrency.'' \\emph{Journal of Finance} 77 (2): 1133--1177.}\n\n\\chg{World Gold Council. 2024. ``Gold's Long-Term Expected Return (GLTER).'' Goldhub research, October 17, 2024. \\url{https://www.gold.org/goldhub/research/golds-long-term-expected-return-glter}.}")
s = s.replace('\\widehat{K}', '\\widehat{G}').replace('\\bar{K}', '\\bar{G}')
s = s.replace('the share of periods in which the verdict flips across', 'the share of periods in which the outcome changes across')
s = s.replace('Expensive (\\%)', 'Not beaten (\\%)')
# drop references no longer cited
r0 = s.index('\\section*{References}'); r1 = s.index('% ============================ APPENDICES')
refs = s[r0:r1]; text = s[:r0] + s[r1:]
plain = re.sub(r'\\chg\{|\\emph\{', '', text)
k = refs.index('\\par\\endgroup')
body, tailstr = refs[:k], refs[k:]
head, *entries = body.split('\n\n')
kept, dropped = [], []
for e in entries:
    e2 = re.sub(r'\\chg\{', '', e).strip()
    if not e2:
        continue
    m = re.search(r'\. (\d{4}[a-z]?)\}?\. ', e2)
    assert m, e2[:80]
    yr = m.group(1)
    first = e2.split(',')[0].split('.')[0].strip()
    key = {'Coin Metrics': 'Coin Metrics', 'DataHub': 'DataHub', 'ff137': 'ff137', 'PlanB': 'PlanB'}.get(first, first.split()[-1].replace('\\~n', '~n'))
    pats = [re.escape(key) + r"[^()\n]{0,60}?\(?" + re.escape(yr) + r"\b", re.escape(key) + r"[^\n]{0,40}\d{4}[a-z]?, " + re.escape(yr) + r"\b"]
    (kept if any(re.search(p, plain) for p in pats) else dropped).append(e)
def _rkey(e):
    e2 = re.sub(r'\\chg\{', '', e).strip()
    first = e2.split(',')[0].split('.')[0].strip()
    first = first.replace('\\c{S}', 'S').replace('\\`{e}', 'e').lower()
    return (first, re.search(r'\. (\d{4}[a-z]?)\}?\. ', e2).group(1))
kept = sorted(kept, key=_rkey)
refs_new = head + '\n\n' + '\n\n'.join(kept) + '\n' + tailstr
s = s[:r0] + refs_new + s[r1:]
print('dropped references:', [re.sub(r'\\chg\{', '', d).split('.')[0] + ' ' + re.search(r'\. (\d{4}[a-z]?)\}?\. ', re.sub(r'\\chg\{', '', d)).group(1) for d in dropped])
clean = s.replace('\\DeclareRobustCommand{\\chg}[1]{{\\color{blue}#1}}', '\\DeclareRobustCommand{\\chg}[1]{{\\color{blue}#1}}\n\\definecolor{blue}{rgb}{0,0,0}', 1)
assert clean != s
open(P + 'manuscript_jai_B.tex', 'w').write(clean)
print('built B')
