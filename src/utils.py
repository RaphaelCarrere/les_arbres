import geopandas as gpd

####################################################################################################
# Jointure
####################################################################################################


def jointure_arbres_iris(df_arbres, gdf_iris):
    """
    Transforme le CSV d'arbres en données géographiques et
    lui ajoute le nom de l'IRIS pour chaque arbre.
    """
    # On sépare 'lat, long' de la colonne geo_point_2d
    df_arbres[['lat', 'lon']] = df_arbres['geo_point_2d'].str.split(',', expand=True).astype(float)

    gdf_arbres = gpd.GeoDataFrame(
        df_arbres,
        geometry=gpd.points_from_xy(df_arbres.lon, df_arbres.lat),
        crs="EPSG:4326"
    )

    # Même système de projection
    gdf_iris = gdf_iris.to_crs(epsg=2154)
    gdf_arbres = gdf_arbres.to_crs(epsg=2154)

    # Jointure
    resultat = gpd.sjoin(gdf_arbres, gdf_iris, how="left", predicate="intersects")

    return resultat


####################################################################################################
# NETTOYAGE DE LA BDD
####################################################################################################

def suppression_colonnes(df):
    """
    Nettoyage : suppression des colonnes redondantes et inutiles.
    """
    colonnes_a_supprimer = ['lat', 'lon', 'geo_point_2d', 'ARRONDISSEMENT', 'index_right', 'TYPE EMPLACEMENT', 'cleabs', 'IDEMPLACEMENT', 'COMPLEMENT ADRESSE', 'LIEU / ADRESSE', 'iris', 'IDBASE']

    df_final = df.drop(columns=[c for c in colonnes_a_supprimer if c in df.columns])

    # 2. Bonus : On peut aussi renommer pour que ce soit plus propre
    # Exemple : passer en minuscules ou enlever les espaces
    df_final.columns = [c.lower().replace(' ', '_').replace('(', '').replace(')', '') for c in df_final.columns]

    return df_final


def nettoyer_valeurs_aberrantes(df):
    """"On traite les Na et les valeurs aberrantes"""

    df_clean = df.dropna(subset=['hauteur_m', 'circonference_cm']).copy()

    # On garde les arbres entre 1m et 40m de hauteur et entre 10cm et 500cm de circonférence
    df_clean = df_clean[
        (df_clean['hauteur_m'].between(1, 40)) & 
        (df_clean['circonference_cm'].between(10, 500))
    ].copy()

    nb_suppr = len(df) - len(df_clean)
    print(f"Nettoyage terminé : {nb_suppr} lignes supprimées (Manquants + Aberrations).")
    print(f"Il reste {len(df_clean)} arbres dans la base.")

    return df_clean
