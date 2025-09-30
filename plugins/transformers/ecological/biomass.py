"""
Plugin for calculating total biomass for ecological data.
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
import logging
from pydantic import Field, field_validator
import os

logger = logging.getLogger(__name__)

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
)
from niamoto.common.exceptions import DatabaseError
from niamoto.common.config import Config


class BiomassConfig(PluginConfig):
    """Configuration for biomass calculation plugin"""

    plugin: str = "biomass"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "individuals_table": "trees", 
            "biomass_field": "biomass",
            "group_field": "plot_id",
            "calculation_method": "direct",  # "direct", "allometric", "custom"
            "dbh_field": "dbh",              # For allometric equations
            "height_field": None,            # Optional for allometric equations
            "wood_density_field": None,      # Optional for allometric equations
            "allometric_equation": "0.0673 * (dbh ** 2.079)",  # Default equation
            "unit": "kg",                    # Output unit (kg, tonnes, etc.)
            "area_normalization": False,     # Whether to normalize by area
            "area_field": None,              # Field containing area value
            "area_unit": "ha"                # Unit of area (ha, m2, etc.)
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
            "individuals_table": "trees",
            "biomass_field": "biomass",
            "group_field": "plot_id",
            "calculation_method": "direct",
            "dbh_field": "dbh",
            "height_field": None,
            "wood_density_field": None,
            "allometric_equation": "0.0673 * (dbh ** 2.079)",
            "unit": "kg",
            "area_normalization": False,
            "area_field": None,
            "area_unit": "ha"
        }
        
        # Apply defaults for missing fields
        for key, default_value in default_params.items():
            if key not in v:
                v[key] = default_value

        # Check all string fields are strings or None
        string_fields = ["individuals_table", "biomass_field", "group_field", 
                         "dbh_field", "height_field", "wood_density_field", 
                         "allometric_equation", "unit", "area_field", "area_unit"]
                         
        for key in string_fields:
            if key in v and v[key] is not None and not isinstance(v[key], str):
                raise ValueError(f"{key} must be a string or None")

        # Check calculation_method is valid
        valid_methods = ["direct", "allometric", "custom"]
        if "calculation_method" in v and v["calculation_method"] not in valid_methods:
            raise ValueError(f"calculation_method must be one of {valid_methods}")

        # If using allometric method, ensure required fields are specified
        if v.get("calculation_method") == "allometric" and not v.get("dbh_field"):
            raise ValueError("dbh_field is required for allometric calculations")

        # Check area_normalization is boolean
        if "area_normalization" in v:
            if not isinstance(v["area_normalization"], bool):
                try:
                    v["area_normalization"] = bool(v["area_normalization"])
                except (ValueError, TypeError):
                    raise ValueError("area_normalization must be a boolean")

            # If normalizing by area, ensure area_field is specified
            if v["area_normalization"] and not v.get("area_field"):
                raise ValueError("area_field is required when area_normalization is True")

        return v


@register("biomass", PluginType.TRANSFORMER)
class Biomass(TransformerPlugin):
    """
    Plugin for calculating total biomass.
    
    This plugin calculates the total biomass for a group (e.g., plot), with options
    for different calculation methods:
    
    1. Direct: Reads biomass values directly from a field
    2. Allometric: Uses allometric equations to calculate biomass from DBH, height, etc.
    3. Custom: Uses a custom equation provided in the configuration
    
    Results can be normalized by area if requested (e.g., kg/ha).
    """
    
    config_model = BiomassConfig
    
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
        """Transform data to calculate total biomass."""
        try:
            # Get parameters from config
            params = config.get("params", {})
            group_id = config.get("group_id")
            
            if group_id is None:
                return {"value": None, "units": params.get("unit", "kg")}

            # Get individuals data for this group
            individuals_table = params.get("individuals_table", "trees")
            biomass_field = params.get("biomass_field", "biomass")
            group_field = params.get("group_field", "plot_id")
            calculation_method = params.get("calculation_method", "direct")
            
            # Get unit information
            unit = params.get("unit", "kg")
            area_normalization = params.get("area_normalization", False)
            area_field = params.get("area_field")
            area_unit = params.get("area_unit", "ha")
            
            # Get individuals data
            individuals_data = self._get_individuals_data(
                individuals_table, group_field, group_id, calculation_method, params
            )
            
            if not individuals_data or len(individuals_data) == 0:
                return {
                    "value": 0, 
                    "units": unit if not area_normalization else f"{unit}/{area_unit}"
                }
            
            # Calculate total biomass based on method
            if calculation_method == "direct":
                # Sum the biomass field values directly
                total_biomass = sum(individual.get(biomass_field, 0) for individual in individuals_data)
            else:
                # Calculate biomass using equations for each individual
                total_biomass = sum(self._calculate_individual_biomass(
                    individual, params) for individual in individuals_data)
            
            # Round to 3 decimal places
            total_biomass = round(total_biomass, 3)
            
            # Normalize by area if requested
            if area_normalization and area_field:
                area_value = self._get_area_value(group_id, params)
                if area_value and area_value > 0:
                    total_biomass = total_biomass / area_value
                    total_biomass = round(total_biomass, 3)
                    final_unit = f"{unit}/{area_unit}"
                else:
                    logger.warning(f"Could not normalize by area: invalid area value {area_value}")
                    final_unit = unit
            else:
                final_unit = unit
            
            return {
                "value": total_biomass,
                "units": final_unit,
                "metadata": {
                    "individual_count": len(individuals_data),
                    "calculation_method": calculation_method
                }
            }

        except Exception as e:
            logger.error(f"Error calculating biomass: {str(e)}")
            return {"value": None, "units": params.get("unit", "kg"), "error": str(e)}
            
    def _get_individuals_data(self, table: str, group_field: str, group_id: int,
                            calculation_method: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get individuals data for a given group."""
        try:
            # Determine which fields we need
            needed_fields = [group_field]
            
            if calculation_method == "direct":
                biomass_field = params.get("biomass_field", "biomass")
                needed_fields.append(biomass_field)
            elif calculation_method in ["allometric", "custom"]:
                dbh_field = params.get("dbh_field")
                if dbh_field:
                    needed_fields.append(dbh_field)
                
                height_field = params.get("height_field")
                if height_field:
                    needed_fields.append(height_field)
                    
                wood_density_field = params.get("wood_density_field")
                if wood_density_field:
                    needed_fields.append(wood_density_field)
            
            # First try to get from database
            try:
                # Log the query parameters for debugging
                logger.debug(f"Getting individuals data with params: table={table}, group_field={group_field}, group_id={group_id}")
                
                fields_str = ", ".join(f'"{field}"' for field in needed_fields if field)
                query = f"""
                    SELECT {fields_str}
                    FROM "{table}"
                    WHERE "{group_field}" = '{group_id}'
                """
                
                logger.debug(f"Executing query: {query}")
                result = self.db.execute_select(query)
                
                if result:
                    # Convert to list of dictionaries
                    return [
                        {needed_fields[i]: value for i, value in enumerate(row) if i < len(needed_fields)}
                        for row in result
                    ]
                    
                logger.debug(f"No results found for group_id {group_id} in table {table}")
                return []
                
            except Exception as db_error:
                logger.error(f"Database error getting individuals data: {str(db_error)}")
                
                # If database query fails, try getting from imports
                if table in self.imports_config:
                    logger.debug(f"Attempting to get data from imports: {table}")
                    return self._get_individuals_from_import(
                        table, group_field, group_id, needed_fields
                    )
                return []
                
        except Exception as e:
            logger.error(f"Error getting individuals data: {str(e)}")
            return []
    
    def _get_individuals_from_import(self, source: str, group_field: str,
                                 group_id: int, needed_fields: List[str]) -> List[Dict[str, Any]]:
        """Get individuals data from imported files."""
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
                return []
            
            # Filter by group
            if group_field in df.columns:
                filtered_df = df[df[group_field] == group_id]
                
                if filtered_df.empty:
                    return []
                
                # Check which needed fields are present
                available_fields = [field for field in needed_fields if field in filtered_df.columns]
                
                # Convert to list of dictionaries with only the needed fields
                return filtered_df[available_fields].to_dict('records')
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting individuals from import: {str(e)}")
            return []
    
    def _calculate_individual_biomass(self, individual: Dict[str, Any], 
                                  params: Dict[str, Any]) -> float:
        """Calculate biomass for an individual using specified method."""
        try:
            calculation_method = params.get("calculation_method")
            
            if calculation_method == "allometric":
                # Get required fields
                dbh_field = params.get("dbh_field", "dbh")
                height_field = params.get("height_field")
                wood_density_field = params.get("wood_density_field")
                
                # Get values
                dbh = individual.get(dbh_field)
                if dbh is None:
                    return 0
                
                height = individual.get(height_field) if height_field else None
                wood_density = individual.get(wood_density_field) if wood_density_field else None
                
                # Apply default allometric equation if not specified
                equation = params.get("allometric_equation", "0.0673 * (dbh ** 2.079)")
                
                # Create local variables for equation evaluation
                locals_dict = {"dbh": dbh}
                if height is not None:
                    locals_dict["height"] = height
                if wood_density is not None:
                    locals_dict["wood_density"] = wood_density
                
                # Evaluate the equation
                return eval(equation, {"__builtins__": {"abs": abs, "pow": pow}}, locals_dict)
            
            elif calculation_method == "custom":
                # For custom, user needs to provide their own equation and field mappings
                # The code structure is similar to allometric but more flexible
                equation = params.get("allometric_equation", "0")
                
                # Create locals dictionary with all available individual fields
                locals_dict = {key: value for key, value in individual.items() if value is not None}
                
                # Evaluate the equation
                return eval(equation, {"__builtins__": {"abs": abs, "pow": pow}}, locals_dict)
            
            else:
                # Should not reach here as we validate the method
                return 0
                
        except Exception as e:
            logger.error(f"Error calculating individual biomass: {str(e)}")
            return 0
    
    def _get_area_value(self, group_id: int, params: Dict[str, Any]) -> Optional[float]:
        """Get area value for normalization."""
        try:
            area_field = params.get("area_field")
            if not area_field:
                return None
                
            # Check if area is in a separate table or same as individuals
            area_table = params.get("area_table", params.get("individuals_table", "plots"))
            group_field = params.get("group_field", "plot_id")
            
            # First try database
            try:
                # Log the query parameters for debugging
                logger.debug(f"Getting area with params: table={area_table}, field={area_field}, group_field={group_field}, group_id={group_id}")
                
                query = f"""
                    SELECT "{area_field}"
                    FROM "{area_table}"
                    WHERE "{group_field}" = '{group_id}'
                    LIMIT 1
                """
                
                logger.debug(f"Executing query: {query}")
                result = self.db.execute_select(query)
                
                if result and result[0][0] is not None:
                    return float(result[0][0])
                
                logger.debug(f"No area value found for group_id {group_id} in table {area_table}")
                    
            except Exception as db_error:
                logger.error(f"Database error getting area: {str(db_error)}")
                
                # If database fails, try imports
                if area_table in self.imports_config:
                    logger.debug(f"Attempting to get area from imports: {area_table}")
                    return self._get_area_from_import(
                        area_table, area_field, group_field, group_id
                    )
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting area value: {str(e)}")
            return None
    
    def _get_area_from_import(self, source: str, area_field: str,
                          group_field: str, group_id: int) -> Optional[float]:
        """Get area value from imported files."""
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
                return None
            
            # Filter by group
            if group_field in df.columns and area_field in df.columns:
                filtered_df = df[df[group_field] == group_id]
                
                if not filtered_df.empty and area_field in filtered_df.columns:
                    area_value = filtered_df[area_field].iloc[0]
                    if area_value is not None:
                        return float(area_value)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting area from import: {str(e)}")
            return None
