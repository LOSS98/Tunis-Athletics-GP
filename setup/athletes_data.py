import pandas as pd
import numpy as np
import re


def process_excel_athlete_data(excel_file_path, sheet_name=0):
    """
    Traite un fichier Excel d'athlètes et retourne 3 tableaux :
    - athletes : informations uniques par athlète avec classes combinées
    - registration : combinaisons sdms/event_name
    - personal_best : performances avec dates, classe athlète et événement nettoyé

    Args:
        excel_file_path: Chemin vers le fichier Excel
        sheet_name: Nom ou index de la feuille (défaut: première feuille)
    """

    try:
        # Lecture du fichier Excel
        print(f"Lecture du fichier Excel : {excel_file_path}")
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)

        print(f"Données chargées : {len(df)} lignes, {len(df.columns)} colonnes")
        print(f"Colonnes disponibles : {list(df.columns)}")

    except FileNotFoundError:
        print(f"Erreur : Fichier non trouvé - {excel_file_path}")
        return None, None, None
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")
        return None, None, None

    # Nettoyage des noms de colonnes (supprimer espaces en début/fin)
    df.columns = df.columns.str.strip()

    # Mapping automatique des colonnes (cherche les colonnes similaires)
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'event' in col_lower and 'name' in col_lower:
            column_mapping[col] = 'event_name'
        elif col_lower in ['sdms', 'sdms id']:
            column_mapping[col] = 'sdms'
        elif col_lower in ['npc']:
            column_mapping[col] = 'npc'
        elif col_lower in ['gender']:
            column_mapping[col] = 'gender'
        elif col_lower in ['lastname', 'family name']:
            column_mapping[col] = 'lastname'
        elif col_lower in ['firstname', 'given name']:
            column_mapping[col] = 'firstname'
        elif col_lower in ['performance']:
            column_mapping[col] = 'performance'
        elif col_lower in ['record_date']:
            column_mapping[col] = 'record_date'
        elif col_lower in ['class', 'entry class']:
            column_mapping[col] = 'class'

    # Appliquer le mapping
    df = df.rename(columns=column_mapping)
    print(f"Colonnes après mapping : {list(df.columns)}")

    # Vérification des colonnes essentielles
    required_columns = ['sdms', 'event_name']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Erreur : Colonnes manquantes - {missing_columns}")
        return None, None, None

    # Nettoyage des données
    initial_rows = len(df)
    df = df.dropna(subset=['sdms'])  # Supprimer les lignes sans SDMS
    df['sdms'] = df['sdms'].astype(str)

    # Nettoyage de la colonne performance
    if 'performance' in df.columns:
        df['performance'] = df['performance'].astype(str)
        # Remplacer 'nan', 'NaN', vides par des valeurs nulles
        df.loc[df['performance'].isin(['nan', 'NaN', '', 'None']), 'performance'] = np.nan

    print(f"Lignes après nettoyage : {len(df)} (supprimées: {initial_rows - len(df)})")

    # 1. Création du tableau ATHLETES
    print("\n=== Création du tableau ATHLETES ===")

    # Grouper par SDMS et combiner les classes
    agg_dict = {
        'firstname': 'first',
        'lastname': 'first',
        'gender': 'first',
        'npc': 'first'
    }

    if 'class' in df.columns:
        agg_dict['class'] = lambda x: ','.join(sorted(set(x.dropna().astype(str))))

    athletes_grouped = df.groupby('sdms').agg(agg_dict).reset_index()

    # Réorganiser les colonnes
    column_order = ['sdms', 'firstname', 'lastname', 'gender', 'class', 'npc']
    available_columns = [col for col in column_order if col in athletes_grouped.columns]
    athletes = athletes_grouped[available_columns]

    print(f"Nombre d'athlètes uniques : {len(athletes)}")

    # 2. Création du tableau REGISTRATION
    print("\n=== Création du tableau REGISTRATION ===")

    registration = df[['sdms', 'event_name']].drop_duplicates().reset_index(drop=True)
    print(f"Nombre d'inscriptions : {len(registration)}")

    # 3. Création du tableau PERSONAL_BEST
    print("\n=== Création du tableau PERSONAL_BEST ===")

    if 'performance' in df.columns:
        # Filtrer uniquement les lignes avec performance non vide
        pb_data = df[df['performance'].notna()].copy()

        # Ajouter une colonne location vide si elle n'existe pas
        if 'location' not in pb_data.columns:
            pb_data['location'] = ''

        # ✨ NOUVELLES COLONNES POUR PERSONAL_BEST ✨

        # Colonne athlete_class (prend la valeur de class)
        if 'class' in pb_data.columns:
            pb_data['athlete_class'] = pb_data['class']
        else:
            pb_data['athlete_class'] = ''

        # Colonne event (nettoyage de event_name)
        def clean_event_name(event_name):
            """
            Nettoie le nom de l'événement :
            - Enlève "Men's " ou "Women's " et l'espace qui suit
            - Enlève la classe à la fin (F00, T00, P00) et l'espace qui précède

            Exemples:
            "Men's Shot Put F11" -> "Shot Put"
            "Women's 100 m T11" -> "100 m"
            """
            if pd.isna(event_name) or event_name == '':
                return ''

            # Convertir en string si ce n'est pas déjà le cas
            event_str = str(event_name)

            # Étape 1: Enlever "Men's " ou "Women's " au début
            event_cleaned = re.sub(r'^(Men\'s\s+|Women\'s\s+)', '', event_str)

            # Étape 2: Enlever la classe à la fin (F00, T00, P00) et l'espace qui précède
            # Pattern: espace + lettre + 2 chiffres à la fin
            event_cleaned = re.sub(r'\s+[FTP]\d{2}$', '', event_cleaned)

            return event_cleaned.strip()

        # Appliquer le nettoyage sur event_name
        pb_data['event'] = pb_data['event_name'].apply(clean_event_name)

        # Sélectionner les colonnes pour personal_best dans le bon ordre
        pb_columns = ['sdms', 'performance', 'location', 'athlete_class', 'event']
        if 'record_date' in pb_data.columns:
            pb_columns.append('record_date')

        available_pb_columns = [col for col in pb_columns if col in pb_data.columns]
        personal_best = pb_data[available_pb_columns].reset_index(drop=True)

        print(f"Nombre de performances : {len(personal_best)}")

        # Affichage d'exemples de transformation event_name -> event
        print(f"\n📝 Exemples de transformation des événements :")
        if len(personal_best) > 0 and 'event_name' in pb_data.columns:
            sample_events = pb_data[['event_name', 'event']].drop_duplicates().head(10)
            for _, row in sample_events.iterrows():
                print(f"   • '{row['event_name']}' -> '{row['event']}'")

    else:
        print("Colonne 'performance' non trouvée - tableau personal_best vide")
        personal_best = pd.DataFrame(
            columns=['sdms', 'performance', 'location', 'athlete_class', 'event', 'record_date'])

    return athletes, registration, personal_best


def save_to_excel(athletes, registration, personal_best, output_filename='processed_athlete_data.xlsx'):
    """Sauvegarder les trois tableaux dans un fichier Excel"""

    try:
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            athletes.to_excel(writer, sheet_name='Athletes', index=False)
            registration.to_excel(writer, sheet_name='Registration', index=False)
            personal_best.to_excel(writer, sheet_name='Personal_Best', index=False)

        print(f"\n✅ Fichier sauvegardé avec succès : {output_filename}")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")
        return False


def analyze_results(athletes, registration, personal_best):
    """Affiche une analyse des résultats"""

    print(f"\n" + "=" * 50)
    print(f"📊 ANALYSE DES RÉSULTATS")
    print(f"=" * 50)

    print(f"🏃 Athlètes uniques : {len(athletes)}")
    print(f"📝 Inscriptions totales : {len(registration)}")
    print(f"🏆 Performances enregistrées : {len(personal_best)}")

    # Athlètes avec plusieurs classes
    if 'class' in athletes.columns:
        multi_class = athletes[athletes['class'].str.contains(',', na=False)]
        print(f"🎯 Athlètes multi-classes : {len(multi_class)}")

        if len(multi_class) > 0:
            print(f"\n📋 Exemples d'athlètes multi-classes :")
            for _, row in multi_class.head(5).iterrows():
                print(f"   • {row['firstname']} {row['lastname']} ({row['sdms']}) : {row['class']}")

    # Répartition par pays
    if 'npc' in athletes.columns:
        country_stats = athletes['npc'].value_counts().head(10)
        print(f"\n🌍 Top 10 pays (nombre d'athlètes) :")
        for country, count in country_stats.items():
            print(f"   • {country} : {count}")

    # Statistiques performances par événement
    if len(personal_best) > 0 and 'event' in personal_best.columns:
        event_stats = personal_best['event'].value_counts().head(10)
        print(f"\n🏃 Top 10 événements (nombre de performances) :")
        for event, count in event_stats.items():
            print(f"   • {event} : {count}")

    # Statistiques par classe d'athlète
    if len(personal_best) > 0 and 'athlete_class' in personal_best.columns:
        class_stats = personal_best['athlete_class'].value_counts().head(10)
        print(f"\n🏅 Top 10 classes (nombre de performances) :")
        for athlete_class, count in class_stats.items():
            print(f"   • {athlete_class} : {count}")

    # Statistiques performances
    if len(personal_best) > 0 and 'record_date' in personal_best.columns:
        pb_with_date = personal_best[personal_best['record_date'].notna()]
        if len(pb_with_date) > 0:
            print(f"\n📅 Performances avec date : {len(pb_with_date)}/{len(personal_best)}")


# UTILISATION DU SCRIPT
if __name__ == "__main__":

    # ⚠️  MODIFIEZ CE CHEMIN VERS VOTRE FICHIER EXCEL ⚠️
    excel_file_path = "C:\\Users\khalil.mzoughi\PycharmProjects\Tunis-Athletics-GP\setup\Final Entries.xlsx"  # 📁 Remplacez par le chemin de votre fichier

    # Optionnel : spécifier le nom de la feuille si nécessaire
    sheet_name = 0  # 0 = première feuille, ou utilisez le nom : "Sheet1"

    print("🚀 Démarrage du traitement...")

    # Traitement du fichier Excel
    athletes, registration, personal_best = process_excel_athlete_data(
        excel_file_path,
        sheet_name=sheet_name
    )

    # Vérification du succès du traitement
    if athletes is not None:

        # Analyse des résultats
        analyze_results(athletes, registration, personal_best)

        # Sauvegarde des résultats
        output_file = "athlete_data_processed.xlsx"
        success = save_to_excel(athletes, registration, personal_best, output_file)

        if success:
            print(f"\n🎉 Traitement terminé avec succès !")
            print(f"📂 Fichier de sortie : {output_file}")

            # Aperçu des données
            print(f"\n👀 APERÇU DES DONNÉES:")
            print(f"\n📋 ATHLETES (5 premiers):")
            print(athletes.head().to_string())

            print(f"\n📋 REGISTRATION (5 premiers):")
            print(registration.head().to_string())

            if len(personal_best) > 0:
                print(f"\n📋 PERSONAL_BEST (5 premiers):")
                print(personal_best.head().to_string())

    else:
        print("❌ Échec du traitement - Vérifiez votre fichier Excel")