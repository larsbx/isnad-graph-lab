# Secondary literature and datasets for time and place

This is a survey of data-analytic work built on the classical sources, made
while adding the temporal and geographic layer (October 2026). Each item has
one of three statuses:

* **Used**: built into the graph.
* **Verified**: we resolved its DOI or URL ourselves.
* **Unverified**: we could not check it, and say what is missing.

## Datasets

| dataset | licence | content | status |
|---|---|---|---|
| **al-Thurayya gazetteer**: Seydi & Romanov, `althurayya/althurayya.github.io` `master/places.geojson` @ `f244e65d`; data DOI 10.34894/6DVTXP | Apache‑2.0 | 2,518 toponyms after Cornu's *Atlas du monde arabo-islamique*: Arabic names and variants, coordinates, settlement type, province, links to Yāqūt/Samʿānī; route network (`routes.json`, about 30 km per travel day) | **used**: `geo.py`, pinned by sha256 |
| **Sanadset 650K**: Mghari, Bouras, El Hibaoui, *Data in Brief* 2022, DOI 10.1016/j.dib.2022.108540; Mendeley 10.17632/5xth87zwb5.5 | CC BY 4.0 | 650,986 reports from 926 books, narrator chains only, with no dates or places | verified; an independent set of chains to cross-check `chains` against |
| **Kaggle «Hadith Narrators (+24K)»**, fahd09 (`all_rawis.csv`), scraped from muslimscholars.info | CC0 on Kaggle; the upstream site's terms are unclear | about 24k narrators with birth/death dates and places | verified (file and licence); column names unverified. A candidate second witness for dates and residences |
| **Wirahman**, "Linking Hadith Narrator Identities Across Heterogeneous Arabic Biographical Databases", arXiv:2607.05424; Zenodo 10.5281/zenodo.21019693 | none stated | links Sanadset ↔ Hawramani (100,915) ↔ muslimscholars (25,247) by name, death year and grade | verified. Death years cover about 22–27% of matched entries; the paper does not check teacher–student chronology |
| **AR‑Sanad 280K**: Mahmoud et al., *Information* 13(2):55, 2022, DOI 10.3390/info13020055 | unverified | narrator DB with death-year text for 18,298 narrators | DOI verified; licence and download unverified |
| **OpenITI** 2023.1.8, Zenodo 10.5281/zenodo.10007820 | CC BY‑NC‑SA 4.0 | about 8,600 machine-readable books, including Mizzī, Dhahabī and Ibn Ḥajar | verified; non-commercial |

## Studies

**Chronology and age structure**

- Romanov, "Algorithmic Analysis of Medieval Arabic Biographical
  Collections", *Speculum* 92 S1 (2017) S226–S246, DOI 10.1086/693970.
  - About 30k biographies of al-Dhahabī's *Taʾrīkh al-Islām*, mined for
    death dates, nisbas and toponyms; regional curves over time.
  - Paywalled; we did not see its figures.
- Romanov, "Observations of a Medieval Quantitative Historian?", *Der Islam*
  94(2) (2017) 462–495, DOI 10.1515/islam-2017-0028. Compares those curves with
  al-Dhahabī's own *al-Amṣār dhawāt al-āthār*.
- Bulliet:
  - "A Quantitative Approach to Medieval Muslim Biographical Dictionaries",
    *JESHO* 13 (1970);
  - *The Patricians of Nishapur* (1972);
  - *Conversion to Islam in the Medieval Period* (1979);
  - "The Age Structure of Medieval Islamic Education", *Studia Islamica* 57
    (1983): very old teachers and very young students as the mechanism of
    elevated (ʿālī) isnads.
  - We cited these from memory and did not check the pages.
- We found no published corpus-scale measurement of teacher–student age gaps.
  `student_age_at_teacher_death` measures it: median 33 years; 9.2% under 10.

**Geography and riḥla**

- Al‑Absi, Kurup, Daoud, Schneider, Zaghouani, Al Marri, Ait Mou,
  "Geo-Spatial and Temporal Analysis of Hadith Narrators", ICICT 2025,
  Springer LNNS 1444, 343–352, DOI 10.1007/978-981-96-6932-5_26. Kernel
  density estimation over birth, residence and death places by generation (on
  the Kaggle set). Hubs: Medina, Baghdad, Nishapur. We saw only the abstract.
- Seydi & Romanov, "Al-Ṯurayyā, the Gazetteer and the Geospatial Model of the
  Early Islamic World", DH2019 Utrecht.

**Network analysis**

- Alam & Schneider, "Social Network Analysis of Hadith Narrators from Sahih
  Bukhari", arXiv:2102.02009. The network is scale-free with 16 communities;
  the centre moves from Mecca/Medina to Kūfa, Baghdad and Central Asia.
- Mairaj Syed, Hadith Network Project (UC Davis): 49,845 transmitters and
  320,393 teacher–student pairs, the same order as this graph (49,845 nodes,
  330,628 edges), which suggests a shared upstream. Results are announced but
  not yet published.

**Common links and isnad-cum-matn**

All of the following are manual studies:

- Juynboll, *Encyclopedia of Canonical Ḥadīth* (2007);
- Motzki, *Analysing Muslim Traditions* (2010);
- Pavlovitch, *The Formation of the Islamic Understanding of Kalāla* (2016);
- Joshua Little, Oxford DPhil (2022) on the ʿĀʾisha marital-age ḥadīth: a
  common link in Hishām b. ʿUrwa in Iraq. We saw only secondary coverage.

We found no automated common-link detection in print; `common_links` does it.

## How the graph compares

| claim in the literature | this graph |
|---|---|
| the hub moves Hijaz → Iraq → Baghdad → Khurasan/Jibal → Syria (Romanov; Alam & Schneider; Al‑Absi et al.) | busiest teacher homes by century: المدينة → الكوفة → بغداد → نيسابور → إصبهان → دمشق (`history.hubs`) |
| the riḥla peaks in the 2nd–3rd centuries | same-city share is lowest in the 3rd century (28%) |
| children's hearing keeps chains short (Bulliet 1983) | 9.2% of documented links have a student under 10 at the teacher's death |

## Next witnesses

The next independent checks on dates and places, in order:

1. join the Kaggle/muslimscholars set by name and death year (as Wirahman
   does) to estimate the error of `death_year` and `iqama`;
2. compare `chains` with Sanadset;
3. replace province centroids by route-network distance (al-Thurayya
   `routes.json`) for travel time.
