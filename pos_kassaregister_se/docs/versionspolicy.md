# Versionspolicy — pos_kassaregister_se

**Gäller från:** 2026-11-02
**Ansvarig:** Vertel Sverige AB

---

## 1. Princip

En ändring av en **reglerad funktion** kräver:

1. höjt versionsnummer,
2. ny tillverkardeklaration,
3. uppdaterat testprotokoll, och
4. inskickning till Skatteverket senast två veckor innan versionen
   tillhandahålls (SKVFS 2021:17 8 kap.).

En ändring **utanför** reglerade funktioner kräver ingen ny deklaration,
men ska loggas med bedömningen att den inte är reglerad — se
`behandlingshistorik.md`.

## 2. Vad som räknas som reglerad funktion

| Reglerad | Exempel |
|---|---|
| Momsberäkning | Ändrad avrundning, ändrade skattesatser i kvittot |
| Kvittoformat | Nytt fält, ändrad ordning, ändrad markeringstext |
| Dataflöde till kontrollenhet | Ändrad signering, ändrat protokoll |
| Spärrar mot ändring | Någon spärr tas bort eller luckras upp |
| Journalminnets innehåll | Ny händelsetyp, ändrad payload |
| Dagrapporternas siffror | Ändrad beräkning av någon post |
| Exportformatet | Ändrat elementnamn, ändrad valutaomräkning |

## 3. Vad som inte räknas som reglerad funktion

| Inte reglerad | Exempel |
|---|---|
| Prestanda | Index, cachning, frågeoptimering |
| Texter utanför kvittot | Hjälptexter, menyer, felmeddelanden |
| Behörigheter | Nya grupper, ändrade ACL |
| Loggning | Nya loggposter som inte når journalminnet |
| Beroenden | Uppgradering av ett bibliotek utan beteendeändring |

Tveksamhet avgörs till det strikta: **är du osäker, behandla ändringen som
reglerad.**

## 4. Versionsnumrering

Modulen följer Odoo:s `18.0.X.Y.Z`-format:

| Del | Höjs när |
|---|---|
| `X` | Ändring av reglerad funktion (kräver ny deklaration) |
| `Y` | Ny funktion som inte är reglerad |
| `Z` | Felrättning utan beteendeändring i reglerad funktion |

## 5. Rutin vid reglerad ändring

1. Utför ändringen i en egen commit med `feat:` eller `fix:`.
2. Höj `X` i `__manifest__.py`.
3. Uppdatera `docs/tillverkardeklaration.md` — ny version, nytt datum.
4. Uppdatera `docs/testprotokoll.md` — kör hela sviten, för in resultatet.
5. Skriv en rad i `docs/behandlingshistorik.md`.
6. Skicka deklaration och utdrag ur protokollet till Skatteverket.
7. Vänta ut tvåveckorsfristen innan utrullning.

## 6. Rutin vid icke-reglerad ändring

1. Utför ändringen.
2. Höj `Y` eller `Z`.
3. Skriv en rad i `docs/behandlingshistorik.md` med bedömningen
   "inte reglerad" och en kort motivering.
4. Ingen inskickning.

## 7. Spärr i utrullningen

En version får inte rullas ut till kunder förrän deklarationen är inskickad
och fristen löpt. Detta gäller även om kunden begär det — regeln är
tvingande. Undantag finns inte.

## 8. Arkivering

Deklaration, testprotokoll och behandlingshistorik sparas i minst sju år
efter det att versionen slutat tillhandahållas. Det följer av
bokföringsskyldigheten och av att en kontrollant ska kunna granska en
historisk version.
