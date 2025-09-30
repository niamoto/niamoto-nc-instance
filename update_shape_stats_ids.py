#!/usr/bin/env python3
"""
Script pour mettre à jour les IDs dans raw_shape_stats.csv
pour qu'ils correspondent aux shape_id dans shape_ref
"""

import pandas as pd
import sqlite3
import sys

# Connexion à la base de données
db_path = "db/niamoto.db"
csv_path = "imports/raw_shape_stats.csv"
output_path = "imports/raw_shape_stats_updated.csv"

# Charger le CSV
print("Chargement du fichier CSV...")
df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
print(f"Nombre de lignes dans le CSV : {len(df)}")

# Connexion à la base
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Récupérer le mapping label -> shape_id depuis shape_ref
print("\nRécupération du mapping depuis shape_ref...")
query = """
SELECT DISTINCT name, shape_id 
FROM shape_ref 
WHERE shape_id IS NOT NULL
ORDER BY name
"""
cursor.execute(query)
mapping = dict(cursor.fetchall())

print(f"Nombre de shapes dans la base : {len(mapping)}")

# Afficher quelques exemples de mapping
print("\nExemples de mapping :")
for i, (name, shape_id) in enumerate(mapping.items()):
    if i < 10:
        print(f"  {name} -> {shape_id}")

# Créer un mapping inverse pour les labels qui ne correspondent pas exactement
# Certains labels dans le CSV peuvent avoir des variations
print("\nRecherche des correspondances pour les labels du CSV...")
unique_labels = df['label'].unique()
label_to_shape_id = {}
not_found = []

for label in unique_labels:
    if label in mapping:
        label_to_shape_id[label] = mapping[label]
    else:
        # Chercher une correspondance exacte dans la base
        query = """
        SELECT shape_id 
        FROM shape_ref 
        WHERE UPPER(TRIM(name)) = UPPER(TRIM(?))
        AND shape_id IS NOT NULL
        """
        cursor.execute(query, (label,))
        result = cursor.fetchone()
        if result:
            label_to_shape_id[label] = result[0]
        else:
            not_found.append(label)

print(f"\nLabels trouvés : {len(label_to_shape_id)}")
print(f"Labels non trouvés : {len(not_found)}")

if not_found:
    print("\nLabels sans correspondance :")
    for label in sorted(not_found)[:20]:  # Afficher les 20 premiers
        print(f"  - {label}")

# Mettre à jour les IDs dans le DataFrame
print("\nMise à jour des IDs...")
df['original_id'] = df['id']  # Sauvegarder l'ID original
df['id'] = df['label'].map(label_to_shape_id)

# Vérifier les lignes sans mapping
no_mapping = df[df['id'].isna()]
if len(no_mapping) > 0:
    print(f"\nAttention : {len(no_mapping)} lignes sans mapping !")
    print("Exemples :")
    print(no_mapping[['original_id', 'label']].drop_duplicates().head(10))

# Supprimer les lignes sans mapping
df_clean = df.dropna(subset=['id'])
print(f"\nNombre de lignes après nettoyage : {len(df_clean)}")

# Supprimer la colonne original_id avant de sauvegarder
df_clean = df_clean.drop(columns=['original_id'])

# Sauvegarder le nouveau fichier
print(f"\nSauvegarde dans {output_path}...")
df_clean.to_csv(output_path, sep=';', index=False, encoding='utf-8')

# Afficher un résumé
print("\nRésumé de la mise à jour :")
print(f"  - Lignes originales : {len(df)}")
print(f"  - Lignes mises à jour : {len(df_clean)}")
print(f"  - Lignes supprimées : {len(df) - len(df_clean)}")

# Afficher quelques exemples de mise à jour
print("\nExemples de mises à jour :")
samples = df_clean[['id', 'label', 'class_object']].drop_duplicates(subset=['id', 'label']).head(10)
for _, row in samples.iterrows():
    print(f"  {row['label']} -> {row['id']}")

conn.close()
print("\nTerminé !")