
## 1.Plugins d'Export

### 1.1 Liste des Plugins d'Export

1. **html_exporter**
   - Description: Export en pages HTML
   - Configuration:
   ```yaml
   plugin: html_exporter
   params:
     template: "taxon_page.html"
     output_dir: "outputs/html"
   ```

2. **json_exporter**
   - Description: Export en fichiers JSON
   - Configuration:
   ```yaml
   plugin: json_exporter
   params:
     indent: 2
     output_dir: "outputs/api"
   ```

3. **csv_exporter**
   - Description: Export en fichiers CSV
   - Configuration:
   ```yaml
   plugin: csv_exporter
   params:
     delimiter: ";"
     output_dir: "outputs/csv"
   ```

### 1.2 Structure d'un Plugin d'Export

```python
@register("exporter_name", PluginType.EXPORTER)
class ExampleExporter(ExporterPlugin):
    """Example exporter plugin"""
    
    class Config(PluginConfig):
        """Configuration validation"""
        output_dir: str
        template: Optional[str]
        
    def export(self, data: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Export data"""
        validated_config = self.Config(**config)
        # Export logic
```

## 2. Widgets

### 2.1 Liste des Widgets

1. **info_grid**
   - Description: Affichage des données structurées en grille
   ```yaml
   plugin: info_grid
   params:
     fields:
       - label: "Nom"
         value: "name"
   ```

2. **interactive_map**
   - Description: Carte interactive avec couches
   ```yaml
   plugin: interactive_map
   params:
     layers:
       - name: "Occurrences"
         geometry: "coordinates"
   ```

3. **bar_plot**
   - Description: Diagramme en barres
   ```yaml
   plugin: bar_plot
   params:
     x_field: "bins"
     y_field: "counts"
   ```

4. **line_plot**
   - Description: Visualisation de séries temporelles
   ```yaml
   plugin: line_plot
   params:
     x_field: "month"
     y_fields: ["temp"]
   ```

5. **donut_chart**
   - Description: Camembert pour proportions
   ```yaml
   plugin: donut_chart
   params:
     value_field: "value"
     label_field: "label"
   ```

6. **radial_gauge**
   - Description: Jauge circulaire avec seuils
   ```yaml
   plugin: radial_gauge
   params:
     value_field: "value"
     max_value: 100
   ```

### 2.2 Structure d'un Widget

```python
@register("widget_name", PluginType.WIDGET)
class ExampleWidget(WidgetPlugin):
    """Example widget plugin"""
    
    class Config(PluginConfig):
        """Configuration validation"""
        width: Optional[str]
        height: Optional[str]
        
    def render(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Render widget HTML/JS"""
        validated_config = self.Config(**config)
        # Rendering logic
        return html
```


---


## Configuration de l'export

Je vois que la configuration actuelle est très liée à Chart.js. Proposons une abstraction plus générique des plugins de visualisation. Voici une approche :

## 1. Types de Plugins d'Export de Base

```yaml
# 1. Plugin d'Affichage d'Informations
info_display:
  description: "Affichage de champs structurés"
  data_format:
    type: object          # Un objet avec des champs nommés
    field_config:        # Configuration par champ
      - name: string     # Nom du champ
      - label: string    # Label d'affichage
      - format: string   # Format (number, text, date...)

# 2. Plugin de Carte
map_display:
  description: "Affichage de données géographiques"
  data_format:
    type: geojson   # Format GeoJSON standard
    style:          # Style générique
      fill: color
      stroke: color
      opacity: number
      radius: number

# 3. Plugin de Graphique
chart_display:
  description: "Visualisation de données"
  types:
    - bar          # Diagramme en barres
    - line         # Courbe
    - pie          # Camembert
    - gauge        # Jauge
  data_format:
    values: array   # Valeurs numériques
    labels: array   # Labels
    series: array   # Séries multiples optionnelles
```

## 2. Exemple de Configuration Simplifiée

```yaml
widgets:
  distribution_map:
    plugin: map_display
    title: "Distribution géographique"
    data:
      source: coordinates
      type: point_collection
    style:
      fill: "#00716b"
      opacity: 0.5
      radius: 2000

  dbh_distribution:
    plugin: chart_display
    type: bar
    title: "Distribution diamétrique (DBH)"
    data:
      x: bins      # Nom du champ pour l'axe X
      y: counts    # Nom du champ pour l'axe Y
    style:
      color: "#4CAF50"
    labels:
      x: "DBH (cm)"
      y: "Nombre d'occurrences"

  wood_density:
    plugin: chart_display
    type: gauge
    title: "Densité de bois"
    data:
      value: mean
      min: 0
      max: 1.2
    style:
      sectors:
        - {min: 0.0, max: 0.4, color: "#f02828"}
        - {min: 0.4, max: 0.8, color: "#e8dd0f"}
        - {min: 0.8, max: 1.2, color: "#049f50"}
    units: "g/cm³"
```

Les avantages :
1. Abstraction des spécificités de Chart.js
2. Description sémantique des données
3. Formats standards (GeoJSON)
4. Style générique réutilisable


### **Plugins de Visualisation (export.yml)**  
**Noms alignés sur les standards du dataviz :**

| **Nom du Plugin**   | **Description**                           | **Clés Standard**                   | **Exemple de Configuration**                                                                                                                    |
| ------------------- | ----------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **info_grid**       | Affiche des données structurées en grille | `fields`, `layout`                  | ```yaml<br>- plugin: info_grid<br>  data_source: general_info<br>  fields:<br>    - {label: "Nom", value: "name"}```                            |
| **interactive_map** | Carte interactive avec couches            | `layers`, `geometry_field`          | ```yaml<br>- plugin: interactive_map<br>  data_source: distribution_map<br>  layers:<br>    - {name: "Occurrences", geometry: "coordinates"}``` |
| **bar_plot**        | Diagramme en barres                       | `x_field`, `y_field`                | ```yaml<br>- plugin: bar_plot<br>  data_source: dbh_distribution<br>  x_field: "bins"<br>  y_field: "counts"```                                 |
| **line_plot**       | Visualisation de séries temporelles       | `x_field`, `y_fields`               | ```yaml<br>- plugin: line_plot<br>  data_source: phenology<br>  x_field: "month"<br>  y_fields: ["flower"]```                                   |
| **donut_chart**     | Camembert pour proportions                | `labels_field`, `values_field`      | ```yaml<br>- plugin: donut_chart<br>  data_source: substrate_distribution<br>  labels_field: "labels"```                                        |
| **radial_gauge**    | Jauge circulaire avec seuils              | `value_field`, `max_value`, `units` | ```yaml<br>- plugin: radial_gauge<br>  data_source: height_stats<br>  value_field: "value"<br>  max_value: 40```                                |
| **stacked_area**    | Zones empilées pour comparaisons          | `x_field`, `stacked_fields`         | ```yaml<br>- plugin: stacked_area<br>  data_source: elevation_distribution<br>  x_field: "altitude"```                                          |

---

### **Améliorations Clés**
1. **Découplage clair entre calculs et rendu**  
   - `binned_distribution` (transformation) ≠ `bar_plot` (visualisation).  
   - Un même plugin de transformation peut alimenter plusieurs visualisations.

2. **Terminologie métier**  
   - `binary_distribution` au lieu de `count_bool` pour décrire une logique de répartition binaire.  
   - `time_series_analysis` au lieu de `temporal_phenology` pour généraliser aux séries temporelles.

3. **Alignement avec les standards**  
   - `bar_plot`/`line_plot` au lieu de `bar_chart`/`line_chart` pour coller aux conventions Python (matplotlib, seaborn).  
   - `interactive_map` au lieu de `map_panel` pour souligner l’interactivité.

4. **Cohérence des clés**  
   - `x_field`/`y_field` pour toutes les visualisations axiales.  
   - `value_field` pour les jauges et indicateurs simples.

### **Plugins de Visualisation (export.yml)**
**Noms de clés standardisées :**  
- `data_source` (référence au champ dans les données transformées)  
- `type` → gardé (ex: `bar_chart`)  
- `options` → paramètres de style  
- `mapping` (pour les correspondances de données)

| **Nom du Plugin** | **Description**                           | **Clés Standard**                   | **Exemple de Configuration**                                                                                                                                        |
| ----------------- | ----------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **info_panel**    | Affiche des données structurées en grille | `fields`, `layout`                  | ```yaml<br>- type: info_panel<br>  data_source: general_info<br>  fields:<br>    - {label: "Nom", value: "name"}<br>    - {label: "Occurrences", value: "count"}``` |
| **map_viewer**    | Carte interactive avec couches            | `layers`, `geometry_field`          | ```yaml<br>- type: map_viewer<br>  data_source: distribution_map<br>  layers:<br>    - {name: "Occurrences", geometry: "coordinates", color: "#1fb99d"}```          |
| **bar_chart**     | Histogramme/Diagramme en barres           | `x_field`, `y_field`, `bins`        | ```yaml<br>- type: bar_chart<br>  data_source: dbh_distribution<br>  x_field: "bins"<br>  y_field: "counts"<br>  options: {title: "DBH Distribution"}```            |
| **line_chart**    | Courbes pour données temporelles          | `x_field`, `y_fields`               | ```yaml<br>- type: line_chart<br>  data_source: phenology<br>  x_field: "month"<br>  y_fields: ["flower", "fruit"]```                                               |
| **donut_chart**   | Camembert/Anneau de répartition           | `labels_field`, `values_field`      | ```yaml<br>- type: doughnut_chart<br>  data_source: substrate_distribution<br>  labels_field: "labels"<br>  values_field: "values"```                               |
| **gauge**         | Jauge avec seuils colorés                 | `value_field`, `max_value`, `units` | ```yaml<br>- type: gauge<br>  data_source: height_stats<br>  value_field: "value"<br>  max_value: 40<br>  units: "m"```                                             |
| **stacked_area**  | Zones empilées pour comparaisons          | `x_field`, `stacked_fields`         | ```yaml<br>- type: stacked_area<br>  data_source: elevation_distribution<br>  x_field: "altitude"<br>  stacked_fields: ["forest", "non_forest"]```                  |
