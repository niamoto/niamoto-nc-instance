"""
Plugin for calculating Shannon's diversity index for ecological data.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np
import math
import logging
from pydantic import Field, field_validator
import os

logger = logging.getLogger(__name__)

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register
)
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class ShannonIndexConfig(PluginConfig):
    """Configuration for Shannon diversity index plugin"""

    plugin: str = "shannon_index"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "species_table": "occurrences", 
            "species_field": "taxon_id",
            "group_field": "plot_id",
            "min_occurrences": 1
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        # Define default values for optional fields
        default_params = {
            "species_table": "occurrences",
            "species_field": "taxon_id",
            "group_field": "plot_id",
            "min_occurrences": 1
        }
        
        # Apply defaults for missing fields
        for key, default_value in default_params.items():
            if key not in v:
                v[key] = default_value

        # Check all string fields are strings
        string_fields = ["species_table", "species_field", "group_field"]
        for key in string_fields:
            if key in v and not isinstance(v[key], str):
                raise ValueError(f"{key} must be a string")

        # Check min_occurrences is an integer
        if "min_occurrences" in v:
            try:
                v["min_occurrences"] = int(v["min_occurrences"])
            except (ValueError, TypeError):
                raise ValueError("min_occurrences must be an integer")

        return v


@register("shannon_index", PluginType.TRANSFORMER)
class ShannonIndex(TransformerPlugin):
    """
    Plugin for calculating Shannon's diversity index.
    
    Shannon's index (H') measures both species richness and evenness. 
    A higher value indicates more diversity.
    
    Formula: H' = -sum(pi * ln(pi)) where pi is the proportion of individuals 
    of species i in the community.
    """
    
    config_model = ShannonIndexConfig
    
    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).dict()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data to calculate Shannon diversity index."""
        try:
            # Get parameters from config
            params = config.get("params", {})
            group_id = config.get("group_id")
            
            if group_id is None:
                return {"value": None, "units": "index"}

            # Get species data for this group
            species_table = params.get("species_table", "occurrences")
            species_field = params.get("species_field", "taxon_id")
            group_field = params.get("group_field", "plot_id")
            min_occurrences = int(params.get("min_occurrences", 1))
            
            # Get species counts
            species_counts = self._get_species_counts(
                species_table, species_field, group_field, group_id
            )
            
            if not species_counts or len(species_counts) == 0:
                return {"value": None, "units": "index", "metadata": {"species_count": 0}}
            
            # Calculate Shannon index
            total_count = sum(species_counts.values())
            if total_count < min_occurrences:
                return {"value": None, "units": "index", "metadata": {"total_count": total_count}}
            
            # Calculate proportions and Shannon index
            shannon_index = 0
            for count in species_counts.values():
                if count <= 0:
                    continue
                proportion = count / total_count
                shannon_index -= proportion * math.log(proportion)
            
            # Round to 3 decimal places
            shannon_index = round(shannon_index, 3)
            
            return {
                "value": shannon_index,
                "units": "index",
                "metadata": {
                    "species_count": len(species_counts),
                    "total_count": total_count,
                    "formula": "H' = -sum(pi * ln(pi))"
                }
            }

        except Exception as e:
            logger.error(f"Error calculating Shannon index: {str(e)}")
            return {"value": None, "units": "index", "error": str(e)}
            
    def _get_species_counts(self, table: str, species_field: str, 
                          group_field: str, group_id: int) -> Dict[Any, int]:
        """Get species counts for a given group."""
        try:
            # First try to get from database
            try:
                logger.debug(f"Getting species counts with params: table={table}, species_field={species_field}, group_field={group_field}, group_id={group_id}")
                
                query = f"""
                        SELECT "{species_field}", COUNT(*) as count
                        FROM "{table}"
                        WHERE "{group_field}" = '{group_id}'
                        GROUP BY "{species_field}"
                    """
                
                logger.debug(f"Executing query: {query}")
                result = self.db.execute_select(query)
                
                if result:
                    species_counts = {row[0]: row[1] for row in result if row[0] is not None}
                    logger.debug(f"Found {len(species_counts)} species with a total of {sum(species_counts.values())} occurrences")
                    return species_counts
                
                logger.debug(f"No results found for group_id {group_id} in table {table}")
                return {}
                
            except Exception as db_error:
                logger.error(f"Database error getting species counts: {str(db_error)}")
                
                # If database query fails, try getting from imports
                if table in self.imports_config:
                    logger.debug(f"Attempting to get data from imports: {table}")
                    return self._get_species_counts_from_import(
                        table, species_field, group_field, group_id
                    )
                return {}
                
        except Exception as e:
            logger.error(f"Error getting species counts: {str(e)}")
            return {}
    
    def _get_species_counts_from_import(self, source: str, species_field: str,
                                    group_field: str, group_id: int) -> Dict[Any, int]:
        """Get species counts from imported files."""
        try:
            import_config = self.imports_config[source]
            
            # Build the full file path
            file_path = os.path.join(
                os.path.dirname(self.config.config_dir), import_config["path"]
            )
            
            # Load data based on type
            if import_config["type"] == "csv":
                df = pd.read_csv(file_path)
            elif import_config["type"] == "vector":
                import geopandas as gpd
                df = gpd.read_file(file_path)
            else:
                logger.error(f"Unsupported import type: {import_config['type']}")
                return {}
            
            # Filter by group
            if group_field in df.columns:
                filtered_df = df[df[group_field] == group_id]
                
                if filtered_df.empty:
                    return {}
                
                if species_field in filtered_df.columns:
                    # Count species occurrences
                    species_counts = filtered_df[species_field].value_counts().to_dict()
                    return species_counts
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting species counts from import: {str(e)}")
            return {}
