import geopandas as gpd


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
