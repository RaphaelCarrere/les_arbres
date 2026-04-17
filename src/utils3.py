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
        <b style="font-size:14px;">🌳 Stade dominant</b><br><br>
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