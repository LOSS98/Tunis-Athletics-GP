import pandas as pd
import numpy as np
import re
from datetime import datetime


def parse_complex_classes(class_str):
    """
    Parse les classes complexes et retourne une liste de classes individuelles

    Exemples:
    - "T46/47/48" -> ["T46", "T47", "T48"]
    - "T46-48" -> ["T46", "T47", "T48"]
    - "T42-47/61-64" -> ["T42", "T43", "T44", "T45", "T46", "T47", "T61", "T62", "T63", "T64"]
    - "F11" -> ["F11"]
    """

    if pd.isna(class_str) or class_str == '':
        return []

    class_str = str(class_str).strip()
    all_classes = []

    # Diviser par "/" pour traiter chaque groupe séparément
    groups = class_str.split('/')

    for group in groups:
        group = group.strip()

        # Vérifier s'il y a un tiret (range)
        if '-' in group:
            # Extraire la lettre préfixe et les numéros
            match = re.match(r'([A-Z]+)(\d+)-(\d+)', group)
            if match:
                prefix = match.group(1)  # T, F, P, etc.
                start_num = int(match.group(2))
                end_num = int(match.group(3))

                # Générer toutes les classes dans la plage
                for num in range(start_num, end_num + 1):
                    all_classes.append(f"{prefix}{num}")
            else:
                # Format non reconnu, ajouter tel quel
                all_classes.append(group)
        else:
            # Pas de tiret, classe simple
            all_classes.append(group)

    # Supprimer les doublons et trier
    unique_classes = sorted(list(set(all_classes)))
    return unique_classes


def parse_date_safe(date_value):
    """
    Parse une date de manière sécurisée

    Returns:
        datetime ou None si parsing impossible
    """
    if pd.isna(date_value):
        return None

    try:
        # Si c'est déjà un datetime
        if isinstance(date_value, datetime):
            return date_value

        # Si c'est un timestamp pandas
        if hasattr(date_value, 'to_pydatetime'):
            return date_value.to_pydatetime()

        # Essayer de parser comme string
        return pd.to_datetime(str(date_value))
    except:
        return None


def remove_duplicates_keep_latest(df):
    """
    Supprime les doublons en gardant le plus récent basé sur record_date

    Critères de doublon : gender, event, class, record_type, region_code

    Returns:
        tuple: (df_cleaned, removed_count, duplicate_info)
    """

    # Colonnes à vérifier pour les doublons
    duplicate_check_columns = ['gender', 'event', 'class', 'record_type', 'region_code']

    # Vérifier que toutes les colonnes existent
    missing_cols = [col for col in duplicate_check_columns if col not in df.columns]
    if missing_cols:
        print(f"⚠️ Colonnes manquantes pour la vérification des doublons : {missing_cols}")
        return df, 0, []

    if 'record_date' not in df.columns:
        print(f"⚠️ Colonne 'record_date' manquante - impossible de déterminer le plus récent")
        return df, 0, []

    # Créer une copie pour le traitement
    df_work = df.copy()

    # Parser les dates de manière sécurisée
    df_work['parsed_date'] = df_work['record_date'].apply(parse_date_safe)

    # Identifier les doublons
    duplicates_mask = df_work.duplicated(subset=duplicate_check_columns, keep=False)

    if not duplicates_mask.any():
        print(f"✅ Aucun doublon détecté !")
        return df, 0, []

    duplicates = df_work[duplicates_mask].copy()

    print(f"\n🔍 DOUBLONS DÉTECTÉS - TRAITEMENT EN COURS...")
    print(f"=" * 60)
    print(f"📊 Nombre de lignes avec doublons : {len(duplicates)}")

    # Grouper les doublons
    duplicate_groups = duplicates.groupby(duplicate_check_columns)

    removed_info = []
    indices_to_remove = []

    print(f"\n📋 ANALYSE DES GROUPES DE DOUBLONS :")
    print(f"-" * 60)

    for group_key, group_df in duplicate_groups:
        gender, event, class_name, record_type, region_code = group_key

        print(f"\n🔸 Groupe : {gender} | {event} | {class_name} | {record_type} | {region_code}")
        print(f"   Nombre de doublons : {len(group_df)}")

        # Trier par date (les plus récentes en premier, NaT/None à la fin)
        group_sorted = group_df.sort_values(
            'parsed_date',
            ascending=False,
            na_position='last'
        )

        # Garder le premier (plus récent)
        keep_index = group_sorted.index[0]
        remove_indices = group_sorted.index[1:].tolist()

        # Informations sur ce qui est gardé vs supprimé
        kept_row = group_sorted.iloc[0]
        removed_rows = group_sorted.iloc[1:]

        print(
            f"   🟢 GARDÉ   : SDMS {kept_row['sdms']} | {kept_row['npc']} | Date: {kept_row['record_date']} | Perf: {kept_row['performance']}")

        for _, removed_row in removed_rows.iterrows():
            print(
                f"   🔴 SUPPRIMÉ: SDMS {removed_row['sdms']} | {removed_row['npc']} | Date: {removed_row['record_date']} | Perf: {removed_row['performance']}")

            removed_info.append({
                'group': group_key,
                'removed_sdms': removed_row['sdms'],
                'removed_npc': removed_row['npc'],
                'removed_date': removed_row['record_date'],
                'removed_performance': removed_row['performance'],
                'kept_sdms': kept_row['sdms'],
                'kept_npc': kept_row['npc'],
                'kept_date': kept_row['record_date'],
                'kept_performance': kept_row['performance']
            })

        indices_to_remove.extend(remove_indices)

    # Supprimer les lignes dupliquées (garder seulement les plus récentes)
    df_cleaned = df_work.drop(indices_to_remove).copy()

    # Supprimer la colonne temporaire
    df_cleaned = df_cleaned.drop('parsed_date', axis=1)

    removed_count = len(indices_to_remove)

    print(f"\n📈 RÉSUMÉ DU NETTOYAGE :")
    print(f"   • Lignes avant nettoyage : {len(df)}")
    print(f"   • Lignes supprimées : {removed_count}")
    print(f"   • Lignes après nettoyage : {len(df_cleaned)}")

    return df_cleaned, removed_count, removed_info


def process_records_excel(excel_file_path, sheet_name=0):
    """
    Traite un fichier Excel de records et expanse les classes complexes

    Args:
        excel_file_path: Chemin vers le fichier Excel
        sheet_name: Nom ou index de la feuille (défaut: première feuille)

    Returns:
        DataFrame avec les lignes dupliquées pour chaque classe et doublons supprimés
    """

    try:
        # Lecture du fichier Excel
        print(f"📖 Lecture du fichier Excel : {excel_file_path}")
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)

        print(f"📊 Données chargées : {len(df)} lignes, {len(df.columns)} colonnes")
        print(f"📋 Colonnes disponibles : {list(df.columns)}")

    except FileNotFoundError:
        print(f"❌ Erreur : Fichier non trouvé - {excel_file_path}")
        return None
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier : {e}")
        return None

    # Nettoyage des noms de colonnes
    df.columns = df.columns.str.strip()

    # Vérification des colonnes requises (sans firstname et lastname)
    required_columns = ['gender', 'event', 'class', 'sdms', 'npc', 'performance',
                        'record_type', 'region_code', 'record_date', 'City', 'Country']

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ Colonnes manquantes : {missing_columns}")
        return None

    # Filtrer les lignes avec SDMS rempli
    initial_rows = len(df)
    df = df[df['sdms'].notna() & (df['sdms'] != '')].copy()
    print(f"🔍 Lignes avec SDMS rempli : {len(df)}/{initial_rows}")

    if len(df) == 0:
        print("⚠️ Aucune ligne avec SDMS trouvée")
        return pd.DataFrame()

    # Création de la colonne location
    df['location'] = df['City'].astype(str) + ", " + df['Country'].astype(str)
    # Nettoyer les cas où City ou Country sont vides
    df['location'] = df['location'].str.replace('nan, ', '').str.replace(', nan', '').str.replace('nan, nan', '')

    print(f"🏃 Expansion des classes complexes...")

    # Liste pour stocker les lignes expansées
    expanded_rows = []

    # Compteurs pour les statistiques
    complex_classes_count = 0
    total_expanded_rows = 0

    for index, row in df.iterrows():
        class_value = row['class']

        # Parser les classes
        individual_classes = parse_complex_classes(class_value)

        if len(individual_classes) > 1:
            complex_classes_count += 1
            print(f"   📝 '{class_value}' -> {individual_classes}")

        # Si aucune classe trouvée, garder la ligne originale
        if not individual_classes:
            individual_classes = [class_value]

        # Créer une ligne pour chaque classe individuelle
        for individual_class in individual_classes:
            new_row = row.copy()
            new_row['class'] = individual_class
            expanded_rows.append(new_row)
            total_expanded_rows += 1

    # Créer le DataFrame final
    result_df = pd.DataFrame(expanded_rows)

    # Sélectionner et réorganiser les colonnes finales (SANS firstname et lastname)
    final_columns = [
        'gender', 'event', 'class', 'sdms', 'npc', 'performance',
        'record_type', 'region_code', 'record_date', 'location'
    ]

    result_df = result_df[final_columns].reset_index(drop=True)

    print(f"\n📈 STATISTIQUES D'EXPANSION :")
    print(f"   • Lignes originales avec SDMS : {len(df)}")
    print(f"   • Classes complexes trouvées : {complex_classes_count}")
    print(f"   • Lignes après expansion : {len(result_df)}")
    print(f"   • Lignes ajoutées par expansion : {len(result_df) - len(df)}")

    # 🚨 SUPPRESSION DES DOUBLONS (GARDER LE PLUS RÉCENT)
    print(f"\n🔧 NETTOYAGE DES DOUBLONS...")
    cleaned_df, removed_count, removed_info = remove_duplicates_keep_latest(result_df)

    if removed_count > 0:
        print(f"\n✅ Nettoyage terminé : {removed_count} doublons supprimés")

    return cleaned_df


def analyze_expanded_data(df):
    """Analyse les données expansées et nettoyées"""

    if df is None or len(df) == 0:
        return

    print(f"\n" + "=" * 60)
    print(f"📊 ANALYSE DES DONNÉES FINALES")
    print(f"=" * 60)

    # Statistiques générales
    print(f"📈 Total des enregistrements : {len(df)}")
    print(f"🏃 Athlètes uniques (SDMS) : {df['sdms'].nunique()}")
    print(f"🏆 Événements uniques : {df['event'].nunique()}")
    print(f"🎯 Classes uniques : {df['class'].nunique()}")
    print(f"🌍 Pays uniques : {df['npc'].nunique()}")

    # Top événements
    print(f"\n🏃 Top 10 événements :")
    event_counts = df['event'].value_counts().head(10)
    for event, count in event_counts.items():
        print(f"   • {event} : {count}")

    # Top classes
    print(f"\n🎯 Top 10 classes :")
    class_counts = df['class'].value_counts().head(10)
    for class_name, count in class_counts.items():
        print(f"   • {class_name} : {count}")

    # Top pays
    print(f"\n🌍 Top 10 pays :")
    npc_counts = df['npc'].value_counts().head(10)
    for npc, count in npc_counts.items():
        print(f"   • {npc} : {count}")

    # Types de records
    if 'record_type' in df.columns:
        print(f"\n🏆 Types de records :")
        record_counts = df['record_type'].value_counts()
        for record_type, count in record_counts.items():
            print(f"   • {record_type} : {count}")

    # Répartition par genre
    if 'gender' in df.columns:
        print(f"\n👥 Répartition par genre :")
        gender_counts = df['gender'].value_counts()
        for gender, count in gender_counts.items():
            print(f"   • {gender} : {count}")


def save_expanded_data(df, output_filename='expanded_records_cleaned.xlsx'):
    """Sauvegarder les données expansées et nettoyées"""

    if df is None or len(df) == 0:
        print("❌ Aucune donnée à sauvegarder")
        return False

    try:
        df.to_excel(output_filename, index=False)
        print(f"\n✅ Fichier sauvegardé avec succès : {output_filename}")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")
        return False


def test_class_parsing():
    """Teste la fonction de parsing des classes"""

    print(f"\n🧪 TEST DE PARSING DES CLASSES:")
    print(f"=" * 40)

    test_cases = [
        "T46/47/48",
        "T46-48",
        "T42-47/61-64",
        "F11",
        "T20/F20",
        "P44-47",
        "T11-13/51-54",
        ""
    ]

    for test_case in test_cases:
        result = parse_complex_classes(test_case)
        print(f"'{test_case}' -> {result}")


# UTILISATION DU SCRIPT
if __name__ == "__main__":

    # Test de parsing (optionnel)
    test_class_parsing()

    # ⚠️  MODIFIEZ CE CHEMIN VERS VOTRE FICHIER EXCEL ⚠️
    excel_file_path = "C:\\Users\khalil.mzoughi\PycharmProjects\Tunis-Athletics-GP\setup\\records.xlsx"  # 📁 Remplacez par le chemin de votre fichier

    # Optionnel : spécifier le nom de la feuille si nécessaire
    sheet_name = 0  # 0 = première feuille, ou utilisez le nom : "Sheet1"

    print(f"\n🚀 DÉMARRAGE DU TRAITEMENT DES RECORDS...")

    # Traitement du fichier Excel
    cleaned_df = process_records_excel(excel_file_path, sheet_name=sheet_name)

    # Vérification du succès du traitement
    if cleaned_df is not None and len(cleaned_df) > 0:

        # Analyse des résultats
        analyze_expanded_data(cleaned_df)

        # Aperçu des données
        print(f"\n👀 APERÇU DES DONNÉES FINALES (5 premières lignes):")
        print(cleaned_df.head().to_string())

        # Vérification finale : plus de doublons
        duplicate_check_columns = ['gender', 'event', 'class', 'record_type', 'region_code']
        final_duplicates = cleaned_df[cleaned_df.duplicated(subset=duplicate_check_columns, keep=False)]

        if len(final_duplicates) == 0:
            print(f"\n✅ VÉRIFICATION FINALE : Aucun doublon restant !")
        else:
            print(f"\n⚠️ ATTENTION : {len(final_duplicates)} doublons restants détectés")

        # Sauvegarde des résultats
        output_file = "expanded_records_cleaned.xlsx"
        success = save_expanded_data(cleaned_df, output_file)

        if success:
            print(f"\n🎉 Traitement terminé avec succès !")
            print(f"📂 Fichier de sortie : {output_file}")
            print(f"📊 Données finales : {len(cleaned_df)} enregistrements uniques")

    else:
        print("❌ Échec du traitement - Vérifiez votre fichier Excel")