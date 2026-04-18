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


def get_top_species(df, column_name='libelle_francais', n=10):
    """
    Calcule le top N des espèces les plus représentées.
    Nettoie les valeurs manquantes pour éviter d'avoir un top "Inconnu".
    """
    # On filtre les valeurs manquantes pour avoir un vrai top
    df_clean = df.dropna(subset=[column_name])
    
    # Comptage
    top_df = df_clean[column_name].value_counts().head(n).reset_index()
    top_df.columns = ['Espece', 'Nombre']
    
    # Calcul du pourcentage pour la culture générale
    total_arbres = len(df_clean)
    top_df['Pourcentage'] = (top_df['Nombre'] / total_arbres * 100).round(2)
    
    return top_df


def get_development_stats(df, column_name='STADE DE DEVELOPPEMENT'):
    """
    Calcule la répartition des stades de développement.
    """
    if column_name not in df.columns:
        # Petite sécurité si le nom de colonne diffère
        return f"Erreur : La colonne {column_name} n'existe pas."
        
    stats = df[column_name].value_counts(normalize=True).reset_index()
    stats.columns = ['Stade', 'Proportion']
    stats['Proportion'] *= 100  # Conversion en %
    
    return stats

import pandas as pd


# ============================================================
# FONCTIONS CARTE INTERACTIVE - STADE DE DÉVELOPPEMENT / IRIS
# ============================================================

import pandas as pd
import geopandas as gpd
import folium
from folium import GeoJson, GeoJsonTooltip, GeoJsonPopup
import json

# Mapping des stades vers 3 catégories
STADE_MAP = {
    'Jeune (arbre)'       : 'Jeune',
    'Jeune'               : 'Jeune',
    'Jeune (arbre)Adulte' : 'Adulte',   
    'Adulte'              : 'Adulte',
    'Adulte (arbre)'      : 'Adulte',
    'Mature'              : 'Vieux',
    'Vieux'               : 'Vieux',
    'Sénescent'           : 'Vieux',
    'Très vieux'          : 'Vieux',
}

def categoriser_stade(df_arbres: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute une colonne 'stade_cat' avec 3 catégories : Jeune, Adulte, Vieux.
    Les arbres sans stade connu sont ignorés (NaN).
    """
    df = df_arbres.copy()
    df['stade_cat'] = df['STADE DE DEVELOPPEMENT'].map(STADE_MAP)
    return df


def agregation_stade_par_zone(df_arbres: pd.DataFrame,
                               groupby_col: str = 'code_iris') -> pd.DataFrame:
    """
    Agrège le nombre d'arbres par zone (iris ou arrondissement) et par stade.
    
    Paramètres
    ----------
    df_arbres   : DataFrame avec colonnes 'stade_cat' et groupby_col
    groupby_col : 'code_iris' ou 'ARRONDISSEMENT'
    
    Retourne un DataFrame avec colonnes :
        groupby_col, n_Jeune, n_Adulte, n_Vieux, total, pct_Jeune, pct_Adulte, pct_Vieux, stade_dominant
    """
    df = categoriser_stade(df_arbres)
    df_valide = df[df['stade_cat'].notna()].copy()

    pivot = (
        df_valide
        .groupby([groupby_col, 'stade_cat'])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # S'assurer que les 3 colonnes existent même si une catégorie est absente
    for col in ['Jeune', 'Adulte', 'Vieux']:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot = pivot.rename(columns={
        'Jeune': 'n_Jeune',
        'Adulte': 'n_Adulte',
        'Vieux': 'n_Vieux'
    })

    pivot['total'] = pivot['n_Jeune'] + pivot['n_Adulte'] + pivot['n_Vieux']

    for stade in ['Jeune', 'Adulte', 'Vieux']:
        pivot[f'pct_{stade}'] = (pivot[f'n_{stade}'] / pivot['total'] * 100).round(1)

    pivot['stade_dominant'] = pivot[['n_Jeune', 'n_Adulte', 'n_Vieux']].idxmax(axis=1).str.replace('n_', '')

    return pivot


def preparer_geodata_stade(gdf_zones: gpd.GeoDataFrame,
                            df_arbres: pd.DataFrame,
                            niveau: str = 'iris') -> gpd.GeoDataFrame:
    """
    Fusionne le GeoDataFrame des zones avec les statistiques de stade.

    Paramètres
    ----------
    gdf_zones : GeoDataFrame des iris (ou arrondissements) avec leur géométrie
    df_arbres : DataFrame df_arbres (issu de jointure_arbres_iris)
    niveau    : 'iris' → groupby sur 'code_iris'
                'arrondissement' → groupby sur 'ARRONDISSEMENT'

    Retourne un GeoDataFrame prêt pour la carte.
    """
    if niveau == 'iris':
        groupby_col = 'code_iris'
        merge_on = 'code_iris'
    else:
        groupby_col = 'ARRONDISSEMENT'
        merge_on = 'ARRONDISSEMENT'

    stats = agregation_stade_par_zone(df_arbres, groupby_col=groupby_col)

    gdf = gdf_zones.copy()
    gdf = gdf.merge(stats, on=merge_on, how='left')

    # Zones sans arbres → 0
    for col in ['n_Jeune', 'n_Adulte', 'n_Vieux', 'total', 'pct_Jeune', 'pct_Adulte', 'pct_Vieux']:
        gdf[col] = gdf[col].fillna(0)
    gdf['stade_dominant'] = gdf['stade_dominant'].fillna('Inconnu')

    # Reprojecter en WGS84 pour Folium
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    return gdf


# Palette de couleurs bleues selon le stade dominant
COULEURS_STADE = {
    'Vieux':  '#1a3a5c',   # bleu très foncé
    'Adulte': '#3d7ab5',   # bleu moyen
    'Jeune':  '#a8d0f0',   # bleu très clair
    'Inconnu': '#cccccc',
}

def _style_stade(feature):
    stade = feature['properties'].get('stade_dominant', 'Inconnu')
    couleur = COULEURS_STADE.get(stade, '#cccccc')
    return {
        'fillColor': couleur,
        'color': '#ffffff',
        'weight': 0.8,
        'fillOpacity': 0.75,
    }

def _highlight(feature):
    return {
        'fillColor': '#f4a261',
        'color': '#e76f51',
        'weight': 2,
        'fillOpacity': 0.9,
    }


def carte_stade_paris(gdf_iris_stats: gpd.GeoDataFrame,
                      gdf_arrdt_stats: gpd.GeoDataFrame = None,
                      titre: str = "Stade dominant des arbres à Paris") -> folium.Map:
    """
    Crée une carte Folium interactive de Paris colorée par stade dominant.

    Paramètres
    ----------
    gdf_iris_stats   : GeoDataFrame retourné par preparer_geodata_stade(..., niveau='iris')
    gdf_arrdt_stats  : (optionnel) même chose pour les arrondissements
                        → affiché à faible zoom, iris à fort zoom
    titre            : titre affiché sur la carte

    Retourne un objet folium.Map.
    """
    m = folium.Map(
        location=[48.8566, 2.3522],
        zoom_start=12,
        tiles='CartoDB positron',
        prefer_canvas=True,
    )

    # --- Couche IRIS ---
    fields_iris = ['nom_iris', 'code_iris', 'stade_dominant',
                   'n_Jeune', 'n_Adulte', 'n_Vieux', 'total',
                   'pct_Jeune', 'pct_Adulte', 'pct_Vieux']
    fields_iris = [f for f in fields_iris if f in gdf_iris_stats.columns]

    aliases_iris = {
        'nom_iris': 'IRIS',
        'code_iris': 'Code IRIS',
        'stade_dominant': '🌳 Stade dominant',
        'n_Jeune': 'Arbres jeunes',
        'n_Adulte': 'Arbres adultes',
        'n_Vieux': 'Arbres vieux',
        'total': 'Total arbres',
        'pct_Jeune': '% Jeunes',
        'pct_Adulte': '% Adultes',
        'pct_Vieux': '% Vieux',
    }

    popup_iris = GeoJsonPopup(
        fields=fields_iris,
        aliases=[aliases_iris.get(f, f) for f in fields_iris],
        localize=True,
        labels=True,
        style="font-family: Arial; font-size: 13px;",
    )
    tooltip_iris = GeoJsonTooltip(
        fields=['nom_iris', 'stade_dominant', 'pct_Jeune', 'pct_Adulte', 'pct_Vieux'],
        aliases=['IRIS', 'Dominant', '% Jeunes', '% Adultes', '% Vieux'],
        localize=True,
    )

    layer_iris = GeoJson(
        gdf_iris_stats.__geo_interface__,
        name="Iris",
        style_function=_style_stade,
        highlight_function=_highlight,
        popup=popup_iris,
        tooltip=tooltip_iris,
    )
    layer_iris.add_to(m)

    # --- Couche Arrondissements (optionnelle) ---
    if gdf_arrdt_stats is not None:
        fields_arrdt = ['ARRONDISSEMENT', 'stade_dominant',
                        'n_Jeune', 'n_Adulte', 'n_Vieux', 'total',
                        'pct_Jeune', 'pct_Adulte', 'pct_Vieux']
        fields_arrdt = [f for f in fields_arrdt if f in gdf_arrdt_stats.columns]

        popup_arrdt = GeoJsonPopup(
            fields=fields_arrdt,
            aliases=[aliases_iris.get(f, f) for f in fields_arrdt],
            localize=True,
            labels=True,
        )
        tooltip_arrdt = GeoJsonTooltip(
            fields=['ARRONDISSEMENT', 'stade_dominant', 'pct_Jeune', 'pct_Adulte', 'pct_Vieux'],
            aliases=['Arrdt', 'Dominant', '% Jeunes', '% Adultes', '% Vieux'],
        )
        layer_arrdt = GeoJson(
            gdf_arrdt_stats.__geo_interface__,
            name="Arrondissements",
            style_function=_style_stade,
            highlight_function=_highlight,
            popup=popup_arrdt,
            tooltip=tooltip_arrdt,
            show=False,  # masquée par défaut, activable via LayerControl
        )
        layer_arrdt.add_to(m)

    # --- Légende ---
    legend_html = """
    <div style="
        position: fixed; bottom: 40px; left: 40px; z-index: 1000;
        background: white; padding: 14px 18px; border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 13px;">
        <b style="font-size:14px;"> Stade dominant</b><br><br>
        <span style="background:#1a3a5c; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Vieux<br>
        <span style="background:#3d7ab5; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Adulte<br>
        <span style="background:#a8d0f0; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Jeune<br>
        <span style="background:#cccccc; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Inconnu
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Titre
    titre_html = f"""
    <div style="
        position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
        z-index: 1000; background: white; padding: 8px 20px; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-family: Arial;
        font-size: 16px; font-weight: bold; color: #1a3a5c;">
        {titre}
    </div>
    """
    m.get_root().html.add_child(folium.Element(titre_html))

    folium.LayerControl(collapsed=False).add_to(m)

    return m

# ============================================================
# FONCTIONS CARTE DENSITÉ + ARBRES REMARQUABLES
# ============================================================

# Palette verte pour la densité
COULEURS_DENSITE = {
    'très élevée': '#1a4d1a',   # vert très foncé
    'élevée':      '#2d7a2d',   # vert foncé
    'moyenne':     '#52a852',   # vert moyen
    'faible':      '#90cc90',   # vert clair
    'très faible': '#d0ecd0',   # vert très clair
}

def calculer_densite_par_zone(df_arbres: pd.DataFrame,
                               gdf_zones: gpd.GeoDataFrame,
                               groupby_col: str = 'code_iris') -> gpd.GeoDataFrame:
    """
    Calcule la densité d'arbres (arbres / km²) par zone.

    Paramètres
    ----------
    df_arbres   : DataFrame df_arbres
    gdf_zones   : GeoDataFrame des zones avec leur géométrie
    groupby_col : colonne de jointure ('code_iris' ou 'ARRONDISSEMENT')

    Retourne un GeoDataFrame avec colonnes :
        groupby_col, n_arbres, superficie_km2, densite, classe_densite
    """
    # Comptage par zone
    comptage = df_arbres.groupby(groupby_col).size().reset_index(name='n_arbres')

    gdf = gdf_zones.copy()
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Superficie en km² (reprojection en 2154 pour calcul métrique)
    gdf_metric = gdf.to_crs(epsg=2154)
    gdf['superficie_km2'] = (gdf_metric.geometry.area / 1e6).round(4)

    gdf = gdf.merge(comptage, on=groupby_col, how='left')
    gdf['n_arbres'] = gdf['n_arbres'].fillna(0).astype(int)
    gdf['densite'] = (gdf['n_arbres'] / gdf['superficie_km2']).round(1)

    # Quintiles pour la classification
    quantiles = gdf[gdf['densite'] > 0]['densite'].quantile([0.2, 0.4, 0.6, 0.8])

    def classer(d):
        if d == 0:       return 'très faible'
        elif d <= quantiles[0.2]: return 'très faible'
        elif d <= quantiles[0.4]: return 'faible'
        elif d <= quantiles[0.6]: return 'moyenne'
        elif d <= quantiles[0.8]: return 'élevée'
        else:            return 'très élevée'

    gdf['classe_densite'] = gdf['densite'].apply(classer)

    return gdf


def extraire_arbres_remarquables(df_arbres: pd.DataFrame,
                                  top_n_hauteur: int = 50,
                                  top_n_circonf: int = 50) -> gpd.GeoDataFrame:
    """
    Extrait les arbres remarquables selon 3 critères :
    - Colonne REMARQUABLE == 'Oui'
    - Top N des plus hauts
    - Top N des plus grosses circonférences

    Retourne un GeoDataFrame avec une colonne 'motif_remarquable'.
    """
    df = df_arbres.copy()

    # Nettoyage
    df['HAUTEUR (m)'] = pd.to_numeric(df['HAUTEUR (m)'], errors='coerce')
    df['CIRCONFERENCE (cm)'] = pd.to_numeric(df['CIRCONFERENCE (cm)'], errors='coerce')

    masque_remarquable = df['REMARQUABLE'].astype(str).str.strip().str.lower() == 'oui'
    masque_hauteur = df['HAUTEUR (m)'] >= df['HAUTEUR (m)'].nlargest(top_n_hauteur).min()
    masque_circonf = df['CIRCONFERENCE (cm)'] >= df['CIRCONFERENCE (cm)'].nlargest(top_n_circonf).min()

    df_rem = df[masque_remarquable | masque_hauteur | masque_circonf].copy()

    # Motif
    def motif(row):
        raisons = []
        if str(row['REMARQUABLE']).strip().lower() == 'oui':
            raisons.append('Remarquable')
        if pd.notna(row['HAUTEUR (m)']) and row['HAUTEUR (m)'] >= df['HAUTEUR (m)'].nlargest(top_n_hauteur).min():
            raisons.append('Top hauteur')
        if pd.notna(row['CIRCONFERENCE (cm)']) and row['CIRCONFERENCE (cm)'] >= df['CIRCONFERENCE (cm)'].nlargest(top_n_circonf).min():
            raisons.append('Top circonférence')
        return ' · '.join(raisons)

    df_rem['motif_remarquable'] = df_rem.apply(motif, axis=1)

    # Conversion en GeoDataFrame
    df_rem = df_rem.dropna(subset=['lat', 'lon'])
    gdf_rem = gpd.GeoDataFrame(
        df_rem,
        geometry=gpd.points_from_xy(df_rem['lon'], df_rem['lat']),
        crs='EPSG:4326'
    )

    return gdf_rem


def _style_densite(feature):
    classe = feature['properties'].get('classe_densite', 'très faible')
    couleur = COULEURS_DENSITE.get(classe, '#d0ecd0')
    return {
        'fillColor': couleur,
        'color': '#ffffff',
        'weight': 0.8,
        'fillOpacity': 0.75,
    }


def carte_densite_paris(gdf_iris_densite: gpd.GeoDataFrame,
                         gdf_arrdt_densite: gpd.GeoDataFrame,
                         gdf_remarquables: gpd.GeoDataFrame,
                         titre: str = "Densité d'arbres à Paris") -> folium.Map:
    """
    Carte Folium interactive avec :
    - Choroplèthe verte de densité d'arbres par IRIS et arrondissement
    - Marqueurs pour les arbres remarquables (tooltip au survol)

    Paramètres
    ----------
    gdf_iris_densite   : sortie de calculer_densite_par_zone(..., niveau='iris')
    gdf_arrdt_densite  : sortie de calculer_densite_par_zone(..., niveau='arrondissement')
    gdf_remarquables   : sortie de extraire_arbres_remarquables()
    """
    m = folium.Map(
        location=[48.8566, 2.3522],
        zoom_start=12,
        tiles='CartoDB positron',
        prefer_canvas=True,
    )

    def _highlight(feature):
        return {'fillColor': '#f4a261', 'color': '#e76f51', 'weight': 2, 'fillOpacity': 0.9}

    # --- Couche IRIS ---
    fields_iris = [c for c in ['nom_iris', 'code_iris', 'n_arbres', 'superficie_km2', 'densite', 'classe_densite']
                   if c in gdf_iris_densite.columns]
    aliases_iris = {
        'nom_iris': 'IRIS', 'code_iris': 'Code IRIS',
        'n_arbres': 'Nombre d\'arbres', 'superficie_km2': 'Superficie (km²)',
        'densite': 'Densité (arbres/km²)', 'classe_densite': 'Classe',
    }

    GeoJson(
        gdf_iris_densite.__geo_interface__,
        name="Densité par IRIS",
        style_function=_style_densite,
        highlight_function=_highlight,
        popup=GeoJsonPopup(
            fields=fields_iris,
            aliases=[aliases_iris.get(f, f) for f in fields_iris],
            localize=True, labels=True,
        ),
        tooltip=GeoJsonTooltip(
            fields=['nom_iris', 'densite', 'classe_densite'],
            aliases=['IRIS', 'Densité (arbres/km²)', 'Classe'],
        ),
    ).add_to(m)

    # --- Couche Arrondissements ---
    fields_arrdt = [c for c in ['ARRONDISSEMENT', 'n_arbres', 'superficie_km2', 'densite', 'classe_densite']
                    if c in gdf_arrdt_densite.columns]
    aliases_arrdt = {
        'ARRONDISSEMENT': 'Arrondissement', 'n_arbres': 'Nombre d\'arbres',
        'superficie_km2': 'Superficie (km²)', 'densite': 'Densité (arbres/km²)',
        'classe_densite': 'Classe',
    }

    GeoJson(
        gdf_arrdt_densite.__geo_interface__,
        name="Densité par arrondissement",
        style_function=_style_densite,
        highlight_function=_highlight,
        popup=GeoJsonPopup(
            fields=fields_arrdt,
            aliases=[aliases_arrdt.get(f, f) for f in fields_arrdt],
            localize=True, labels=True,
        ),
        tooltip=GeoJsonTooltip(
            fields=['ARRONDISSEMENT', 'densite', 'classe_densite'],
            aliases=['Arrondissement', 'Densité (arbres/km²)', 'Classe'],
        ),
        show=False,
    ).add_to(m)

    # --- Marqueurs arbres remarquables ---
    cluster = folium.FeatureGroup(name=" Arbres remarquables")

    for _, row in gdf_remarquables.iterrows():
        hauteur = f"{row['HAUTEUR (m)']} m" if pd.notna(row['HAUTEUR (m)']) else 'N/A'
        circonf = f"{row['CIRCONFERENCE (cm)']} cm" if pd.notna(row['CIRCONFERENCE (cm)']) else 'N/A'
        libelle = row.get('LIBELLE FRANCAIS', 'Inconnu')
        motif   = row.get('motif_remarquable', '')

        tooltip_txt = (
            f"<b>{libelle}</b><br>"
            f"{motif}<br>"
            f" Hauteur : {hauteur}<br>"
            f" Circonférence : {circonf}"
        )

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color='#7b3f00',
            fill=True,
            fill_color='#c8a96e',
            fill_opacity=0.85,
            weight=1.5,
            tooltip=folium.Tooltip(tooltip_txt),
        ).add_to(cluster)

    cluster.add_to(m)

    # --- Légende densité ---
    legend_html = """
    <div style="
        position: fixed; bottom: 40px; left: 40px; z-index: 1000;
        background: white; padding: 14px 18px; border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 13px;">
        <b style="font-size:14px;"> Densité d'arbres</b><br><small>(arbres / km²)</small><br><br>
        <span style="background:#1a4d1a; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Très élevée<br>
        <span style="background:#2d7a2d; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Élevée<br>
        <span style="background:#52a852; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Moyenne<br>
        <span style="background:#90cc90; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Faible<br>
        <span style="background:#d0ecd0; display:inline-block; width:18px; height:18px;
              border-radius:3px; vertical-align:middle; margin-right:6px;"></span> Très faible<br><br>
        <span style="background:#c8a96e; display:inline-block; width:12px; height:12px;
              border-radius:50%; vertical-align:middle; margin-right:6px;
              border: 1.5px solid #7b3f00;"></span> Arbre remarquable
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Titre
    titre_html = f"""
    <div style="
        position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
        z-index: 1000; background: white; padding: 8px 20px; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-family: Arial;
        font-size: 16px; font-weight: bold; color: #1a4d1a;">
        {titre}
    </div>
    """
    m.get_root().html.add_child(folium.Element(titre_html))

    folium.LayerControl(collapsed=False).add_to(m)

    return m
