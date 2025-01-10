import streamlit as st
import pandas as pd
import re
import math
import datetime
from fillpdf import fillpdfs
import os
import glob

# Az adatok betöltése és előfeldolgozása
def load_data(file_path):
    try:
        # Az Excel fájl beolvasása
        df = pd.read_excel(file_path, header=None)

        # Az első két sor törlése
        df = df.iloc[2:].reset_index(drop=True)

        # Új oszlopnevek beállítása
        df.columns = [
            "Cikkszám", "Cikktípus", "Cikknév", "Mennyiség", "Me.e", "Egységár", "Érték", 
            "Deviza", "Beszerzés dátuma", "Beszerzési ár", "Raktár", "Rekesz", "Vonalkód"
        ]

        return df
    except Exception as e:
        st.error(f"Hiba a fájl betöltésekor: {e}")
        return pd.DataFrame()

# Függvény szövegek tisztítására és összehasonlítására
def match_string(search, target):
    # Szóközök és speciális karakterek eltávolítása, kisbetűsre alakítás
    clean_search = re.sub(r'\W+', '', search.lower())
    clean_target = re.sub(r'\W+', '', target.lower())
    return clean_search in clean_target

# Függvény biztonságos lebegőpontos átalakításhoz
def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return None  # None értéket ad vissza, ha az átalakítás sikertelen

# Függvény ár kiszámítására árréssel
def calculate_price(cikktipus, beszerzesi_ar, kisgepek_arres, tvk_arres, tuzhelyek_arres, normal_arres):
    if cikktipus in [129, 128, 161, 162, 166]:
        margin = kisgepek_arres
    elif cikktipus in [177]:
        margin = tvk_arres
    elif cikktipus in [151, 152, 153]:
        margin = tuzhelyek_arres
    else:
        margin = normal_arres

    try:
        # Ár kiszámítása árréssel és ÁFA-val
        price = beszerzesi_ar * (1 + margin / 100) * 1.27

        # Ár kerekítése a legközelebbi 999-re
        rounded_price = math.ceil(price / 1000) * 1000 - 1

        return rounded_price
    except TypeError:
        return None

# Árrés kiszámítása
def calculate_arres(price, beszerzesi_ar):
    try:
        return round(((price / 1.27) - beszerzesi_ar) / beszerzesi_ar * 100, 1)  # ÁFA levonása és százalékos számítás
    except TypeError:
        return None

# Alapértelmezett inicializálás a session state-ben
if "increased_prices" not in st.session_state:
    st.session_state.increased_prices = None    

# Excel fájl betöltése
def load_excel(file):
    return pd.read_excel(file)

# Beszerzési ár ellenőrzése
def beszarak():
    # Felület megjelenítése
    st.title("Beszerzési ár változás ellenőrzése")
    st.write("Ellenőrizd a beszerzési ár változását.")

    if st.button("Indít"):
        try:
            # Fájlok betöltése
            bk_path = "C:\\Digit nagyker\\árcimkék\\bk.xlsx"
            bk_regi_path = "C:\\Digit nagyker\\árcimkék\\bk_regi.xlsx"
            kitoltott_folder = "C:\\Digit nagyker\\árcimkék\\kitöltött"

            # Kitöltött fájlok törlése
            if os.path.exists(kitoltott_folder):
                files = glob.glob(os.path.join(kitoltott_folder, "*"))
                for file in files:
                    if os.path.isfile(file):  # Csak fájlokat töröl
                        os.remove(file)
                st.write(f"A '{kitoltott_folder}' könyvtár összes fájlja törölve lett.")
            else:
                st.warning(f"A '{kitoltott_folder}' könyvtár nem található.")

            # Feltételezve, hogy a 'Cikkszám' oszlop a harmadik sorban található (index 2)
            bk_df = pd.read_excel(bk_path, header=2)
            bk_regi_df = pd.read_excel(bk_regi_path, header=2)

            # Feltételezve, hogy a 'Cikkszám', 'Beszerzési ár', és 'Cikknév' oszlopok léteznek
            merge_df = pd.merge(bk_df, bk_regi_df, on='Cikkszám', suffixes=("", "_regi"))

            # Ár változás számítása
            merge_df['Különbség'] = merge_df['Beszerzési ár'] - merge_df['Beszerzési ár_regi']

            # Csak azok a tételek, ahol az ár nőtt
            increased_prices_df = merge_df[merge_df['Különbség'] > 0]

            # Eredmények tárolása session state-ben
            if not increased_prices_df.empty:
                st.session_state.increased_prices = increased_prices_df[['Cikkszám', 'Cikknév', 'Beszerzési ár', 'Beszerzési ár_regi', 'Különbség']]
                st.write("Talált tételek, ahol az ár nőtt:")
            else:
                st.session_state.increased_prices = None
                st.write("Nincs olyan tétel, ahol a beszerzési ár nőtt volna.")

        except Exception as e:
            st.error(f"Hiba történt: {e}")

    # Eredmények megjelenítése (ha már léteznek a session state-ben)
    if st.session_state.increased_prices is not None:
        st.dataframe(st.session_state.increased_prices)

    if st.button("Árak visszatöltése"):
        st.write("Excel fájl megjelenítése")

    # Feltöltési gomb
    uploaded_file = st.file_uploader("Tölts fel egy Excel fájlt", type="xlsx")
    
    if uploaded_file is not None:
        # Ellenőrizni, hogy az adatokat már beolvastuk-e
        if 'data' not in st.session_state:
            st.session_state.data = load_excel(uploaded_file)
        
        # Megjeleníteni a beolvasott adatokat
        st.write("A beolvasott adat:")
        st.dataframe(st.session_state.data)

# Streamlit alkalmazás
def main():
    st.title("Árcímke Kereső")

    # Árrés beállítások az oldalsávban
    st.sidebar.header("Árrés beállítások")
    normal_arres = st.sidebar.number_input("Normál árrés (%)", value=18, step=1)
    kisgepek_arres = st.sidebar.number_input("Kisgépek árrés (%)", value=25, step=1)
    tvk_arres = st.sidebar.number_input("TV-k árrés (%)", value=10, step=1)
    tuzhelyek_arres = st.sidebar.number_input("Tűzhelyek árrés (%)", value=10, step=1)

    # Fájl betöltése
    file_path = r"C:\\Digit nagyker\\árcimkék\\bk.xlsx"
    data = load_data(file_path)

    if not data.empty:
        st.markdown(
            """
            <style>
            .custom-input input {
                background-color: yellow;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Keresés")
        search_input = st.text_input(
            "Adja meg a keresendő kifejezést (Cikknév alapján):",
            key="search_input",
            placeholder="Írjon be egy kifejezést"
        )

        if search_input:
            filtered_data = data[data['Cikknév'].apply(lambda x: match_string(search_input, str(x)))]

            if not filtered_data.empty:
                st.subheader("Találatok")
                selected_index = st.selectbox(
                    "Válassza ki, melyik adatot szeretné használni",
                    options=filtered_data.index,
                    format_func=lambda x: f"Cikkszám: {filtered_data.loc[x, 'Cikkszám']} - {filtered_data.loc[x, 'Cikknév']}"
                )

                selected_row = filtered_data.loc[selected_index]
                st.write("Kiválasztott sor:")
                st.json(selected_row.to_dict())

                # Bemeneti mezők létrehozása a kiválasztott értékekkel

                # A kiválasztott sor lekérése
                selected_row = filtered_data.loc[selected_index]

                # További mezők létrehozása
                beszerzesi_ar_float = safe_float(selected_row['Beszerzési ár'])
                cikktipus = selected_row['Cikktípus']
                cikktipus = int(cikktipus) if isinstance(cikktipus, (int, str)) and str(cikktipus).isdigit() else cikktipus

                # Ár és árrés kiszámítása
                price = calculate_price(cikktipus, beszerzesi_ar_float, kisgepek_arres, tvk_arres, tuzhelyek_arres, normal_arres)
                arres = calculate_arres(price, beszerzesi_ar_float)

                # Egy sor létrehozása az ár, árrés és lenyíló listák számára
                cols_price_arres = st.columns(6)
                
                # Ár bemeneti mező, amely frissíti az árrést
                price_input = cols_price_arres[0].text_input("Ár", value=int(price) if price else "N/A", key=f"price_{selected_row['Cikkszám']}")

                # Ellenőrizze, hogy a felhasználó manuálisan módosította-e az árat
                try:
                    manual_price = float(price_input)
                except ValueError:
                    manual_price = price  # Ha nem érvényes, használja a kiszámított árat

                # Árrés újraszámítása az új ár alapján
                arres = calculate_arres(manual_price, beszerzesi_ar_float)

                cols_price_arres[1].text_input("Árrés", value=arres if arres else "N/A", key=f"arres_{selected_row['Cikkszám']}")

                # Lenyíló lista hozzáadása a kiválasztáshoz
                dropdown_value = cols_price_arres[2].selectbox("Cimke kiválasztása", options=["Normál", "Csereakció",  "Akció", "Kicsi", "Kiemelt"], key=f"dropdown_{selected_row['Cikkszám']}")

                # Ha "Csereakció" van kiválasztva, új bemeneti mező az ár + 10000 számára
                if dropdown_value == "Csereakció":
                    csereakcio_price = round(manual_price + 10000)
                    csereakcio_price_input = cols_price_arres[3].text_input("Csereakció Ár", value=str(int(csereakcio_price)), key=f"csereakcio_price_{selected_row['Cikkszám']}")
                    try:
                        csereakcio_manual_price = float(csereakcio_price_input)
                    except ValueError:
                        csereakcio_manual_price = csereakcio_price  # Ha nem érvényes, használja a kiszámított árat
                else:
                    csereakcio_manual_price = None

                # Ha "Akció" van kiválasztva, új bemeneti mező az ár + 3000 számára
                if dropdown_value == "Akció":
                    akcio_price = round(manual_price + 3000)
                    akcio_price_input = cols_price_arres[3].text_input("Akció", value=str(int(akcio_price)), key=f"akcio_price_{selected_row['Cikkszám']}")
                    try:
                        akcio_manual_price = float(akcio_price_input)
                    except ValueError:
                        akcio_manual_price = akcio_price  # Ha nem érvényes, használja a kiszámított árat
                else:
                    akcio_manual_price = None
                
                # Lista inicializálása a session state-ben, ha még nem történt meg
                if 'table_data' not in st.session_state:
                    st.session_state['table_data'] = []

                # Gomb az adatok listához adásához
                if st.button("Listába"):

                    manual_price = float(manual_price[0]) if isinstance(manual_price, tuple) else float(manual_price)
                    beszerzesi_ar = float(selected_row['Beszerzési ár'])  # A kiválasztott sorból
                    arres_tomeg = round(manual_price - (beszerzesi_ar * 1.27)) if manual_price and beszerzesi_ar else None

                    
                    formatted_arres = f"{arres:.1f}" if arres is not None else "N/A"  # Árrés % formázása (pl. 27,7)
                    #formatted_arres_tomeg = round(arres_tomeg) if arres_tomeg is not None else "N/A"  # Kerekítés egész számra
                    
                    # Új sor: Csereakció ár formázása
                    formatted_csereakcio_price = None
                    if csereakcio_manual_price:
                        csereakcio_manual_price = float(csereakcio_manual_price[0]) if isinstance(csereakcio_manual_price, tuple) else float(csereakcio_manual_price)
                        formatted_csereakcio_price = int(round(csereakcio_manual_price))  # Csereakció ár konvertálása és kerekítése

                    # Új sor: Akció ár formázása
                    formatted_akcio_price = None
                    if akcio_manual_price:
                        akcio_manual_price = float(akcio_manual_price[0]) if isinstance(akcio_manual_price, tuple) else float(akcio_manual_price)
                        formatted_akcio_price = int(round(akcio_manual_price))  # akció ár konvertálása és kerekítése

                     # Beszerzés dátum formázása (241002 formátum)
                    beszerzes_datum = selected_row['Beszerzés dátuma']
                    if isinstance(beszerzes_datum, str):
                        try:
                            date_obj = datetime.datetime.strptime(beszerzes_datum, "%y.%m.%d")
                            formatted_datum = date_obj.strftime("%y%m%d")
                        except ValueError:
                            formatted_datum = "Hibás dátum"
                    else:
                        formatted_datum = "Hibás dátum"    
                    
                    entry = {
                        "Cikkszám": selected_row['Cikkszám'],
                        "Cikknév": selected_row['Cikknév'],
                        "Ár": int(manual_price),
                        "Árrés (%)": formatted_arres,
                        "Árrés tömeg": arres_tomeg,
                        "Címke": dropdown_value,
                        "Beszerzés dátuma": formatted_datum,
                    }
                    if formatted_csereakcio_price is not None:
                        entry["Csereakció Ár"] = formatted_csereakcio_price
                    #st.session_state['table_data'].append(entry)
                    if formatted_akcio_price is not None:
                        entry["Akció"] = formatted_akcio_price
                    st.session_state['table_data'].append(entry)
                # Display the table
                # Az 'st.session_state['table_data']' alapján kell létrehozni a 'table_data'-t
                if st.session_state['table_data']:
                    st.subheader("Listázott adatok")
                    table_data = pd.DataFrame(st.session_state['table_data'])  # Az előzőleg hozzáadott adatok táblázatba rendezése
                    
                    # 'Ár' és 'Csereakció Ár' oszlopok formázása
                    if "Ár" in table_data.columns:
                        table_data["Ár"] = table_data["Ár"].apply(lambda x: f"{x:,.0f}".replace(",", " "))  # Ezres elválasztó hozzáadása

                    if "Csereakció Ár" in table_data.columns:
                        table_data["Csereakció Ár"] = table_data["Csereakció Ár"].apply(lambda x: f"{x:,.0f}".replace(",", " "))  # Ezres elválasztó hozzáadása
                    
                    if "Akció" in table_data.columns:
                        table_data["Akció"] = table_data["Akció"].apply(lambda x: f"{x:,.0f}".replace(",", " "))  # Ezres elválasztó hozzáadása
                    
                    
                    st.table(table_data)

                    # "Címke kiválasztása" mező
                    #label_type = st.selectbox("Címke kiválasztása", ["Csereakció", "Normál"])

                    output_folder = r"C:\\Digit nagyker\\árcimkék\\kitöltött"
                    os.makedirs(output_folder, exist_ok=True)

                    for index, row in table_data.iterrows():
                        # PDF fájl útvonala a táblázat Címke oszlopa alapján
                        if row["Címke"] == "Csereakció":
                            input_pdf_path = r"C:\\Digit nagyker\\árcimkék\\Arcimke 66x57_csere.pdf"
                        elif row["Címke"] == "Normál":
                            input_pdf_path = r"C:\\Digit nagyker\\árcimkék\\Arcimke 66x57_normal.pdf"
                        elif row["Címke"] == "Akció":
                            input_pdf_path = r"C:\\Digit nagyker\\árcimkék\\Arcimke 66x57_akcio.pdf"
                        else:
                            print(f"Hiba: Érvénytelen Címke érték: {row['Címke']} a {row['Cikkszám']} cikkszámnál.")
                            continue  # Ha érvénytelen a Címke értéke, kihagyjuk az adott sort

                        # Kitöltendő mezők összeállítása
                        filled_data = {
                            "cikknév": row["Cikknév"],
                            "cikkszám": f"{row['Cikkszám']} - 20010{row['Beszerzés dátuma']}",
                            "ár": row["Ár"],
                            "csere ár": row.get("Csereakció Ár", ""),  # Csereakció ár opcionális
                            "akció": row.get("Akció", "")  # Csereakció ár opcionális
                        }

                        output_pdf_path = os.path.join(output_folder, f"Árcímke_{row['Cikkszám']}.pdf")

                        # PDF mezők kitöltése és mentése
                        try:
                            fillpdfs.write_fillable_pdf(input_pdf_path, output_pdf_path, filled_data)
                        except Exception as e:
                            print(f"Hiba a PDF írásakor a következő cikknél: {row['Cikknév']} ({row['Cikkszám']}): {e}")

                    print("PDF fájlok sikeresen létrehozva és kitöltve!")
                    st.success("PDF fájlok sikeresen létrehozva és kitöltve!")

                else:
                    st.warning("Nincs találat a megadott kifejezésre.")


                # Két vagy több oszlopot hozunk létre a gombok számára
                col1, col2, col3 = st.columns(3)

                # Adatok mentése gomb
                with col1:
                    if st.button("Adatok mentése"):
                        if st.session_state.get('table_data'):  # Ellenőrizzük, hogy van-e adat a táblázatban
                            df = pd.DataFrame(st.session_state['table_data'])

                            # Mentési mappa és fájlnév beállítása
                            save_dir = r"C:\Digit nagyker\árcimkék\mentett árazások"
                            os.makedirs(save_dir, exist_ok=True)  # A mappa létrehozása, ha nem létezik
                            current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                            file_name = f"árazás_{current_time}.xlsx"
                            file_path = os.path.join(save_dir, file_name)

                            # Fájl mentése
                            df.to_excel(file_path, index=False)
                            st.success(f"Az adatok elmentésre kerültek a következő fájlba: {file_path}")
                        else:
                            st.warning("Nincs elmenthető adat!")

                # Nyomtatás gomb
                with col2:
                    if st.button("Nyomtatás"):
                        # Itt adhatod meg a nyomtatás logikáját
                        st.write("Nyomtatás folyamatban...")
                        # Például egy PDF generálás vagy más nyomtatási művelet

                # UNAS előkészítés gomb
                with col3:
                    if st.button("UNAS előkészítés"):
                        # Itt adhatod meg az UNAS előkészítés logikáját
                        st.write("UNAS előkészítés folyamatban...")
                        # Itt például fájlformátumok előkészítése, adatok rendezése, stb.


if __name__ == "__main__":
    main()
