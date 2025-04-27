import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import warnings
import matplotlib.pyplot as plt
import contextily as cx
import os # For creating directory
from pyproj import CRS
import numpy as np
from shapely.ops import nearest_points
from scipy.spatial import distance

# Suppress pandas SettingWithCopyWarning, use with caution
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)


def load_ais_data(csv_path: str) -> pd.DataFrame:
    """Loads AIS data from a CSV file, parses timestamps, cleans, and sorts it."""
    try:
        print(f"Loading AIS data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Basic validation: Check for essential columns
        required_cols = ['MMSI', 'BaseDateTime', 'LAT', 'LON']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV must contain columns: {required_cols}")

        # Data Cleaning and Type Conversion
        print("Preprocessing data...")
        df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'], errors='coerce')
        df.dropna(subset=['BaseDateTime', 'LAT', 'LON', 'MMSI'], inplace=True) # Drop rows where essential info is missing
        
        # Ensure MMSI is integer
        df['MMSI'] = df['MMSI'].astype(int)

        # Filter invalid LAT/LON (optional, but good practice)
        df = df[(df['LAT'] >= -90) & (df['LAT'] <= 90) & (df['LON'] >= -180) & (df['LON'] <= 180)]

        # Sort data for trajectory creation
        df.sort_values(by=['MMSI', 'BaseDateTime'], inplace=True)
        
        print(f"Loaded and preprocessed {len(df)} data points.")
        return df

    except FileNotFoundError:
        print(f"Error: File not found at {csv_path}")
        return pd.DataFrame() # Return empty DataFrame on error
    except ValueError as ve:
        print(f"Error processing CSV: {ve}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return pd.DataFrame()


def create_trajectories(df: pd.DataFrame, min_points: int = 2) -> dict[int, LineString]:
    """Converts AIS DataFrame points into LineString trajectories per MMSI."""
    print("Creating trajectories...")
    if df.empty:
        print("Input DataFrame is empty. Cannot create trajectories.")
        return {}
        
    try:
        # Create GeoDataFrame
        geometry = [Point(xy) for xy in zip(df['LON'], df['LAT'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326') # WGS84

        trajectories = {}
        grouped = gdf.groupby('MMSI')

        for mmsi, group in grouped:
            # Need at least min_points points to form a line
            if len(group) >= min_points:
                # Sort points within the group just in case (should be sorted already)
                group = group.sort_values(by='BaseDateTime')
                # Create LineString from the sorted points
                trajectory = LineString(group['geometry'].tolist())
                trajectories[mmsi] = trajectory
            # else:
                # print(f"Skipping MMSI {mmsi}: only {len(group)} points (min required: {min_points}).")

        print(f"Created {len(trajectories)} trajectories.")
        return trajectories

    except Exception as e:
        print(f"An unexpected error occurred during trajectory creation: {e}")
        return {}


def estimate_utm_crs(lat, lon):
    """Estimates the UTM CRS based on a latitude and longitude."""
    return CRS.from_dict({
        'proj': 'utm',
        'zone': int((lon + 180) / 6) + 1,
        'south': lat < 0,
        'ellps': 'WGS84',
        'datum': 'WGS84',
        'units': 'm'
    })

def count_self_proximity_hits(trajectory: LineString, proximity_threshold_meters: float = 200.0) -> int:
    """Counts pairs of non-adjacent points within a threshold distance.

    Args:
        trajectory: The trajectory as a shapely LineString (assumed EPSG:4326).
        proximity_threshold_meters: The distance threshold in meters.
                                    Defaults to 200m.

    Returns:
        The count of non-adjacent point pairs closer than the threshold.
    """
    hit_count = 0
    if trajectory is None or trajectory.is_empty:
        return hit_count
        
    coords_list = list(trajectory.coords)
    if len(coords_list) < 5:
        return hit_count
    
    try:
        # Project to UTM (code remains the same as before)
        gs = gpd.GeoSeries([trajectory], crs='EPSG:4326')
        centroid = trajectory.centroid
        target_crs = 'EPSG:3857' # Fallback
        if isinstance(centroid, Point) and not centroid.is_empty:
            try:
                target_crs = estimate_utm_crs(centroid.y, centroid.x)
            except Exception:
                pass # Use fallback
        gs_projected = gs.to_crs(target_crs)
        projected_line = gs_projected.iloc[0]
        
        if projected_line is None or projected_line.is_empty:
            return hit_count
        
        coords = np.array(projected_line.coords)
        total_points = len(coords)
        if total_points < 5:
            return hit_count
            
        adjacency_window = max(2, int(total_points * 0.1))
        
        for i in range(total_points):
            for j in range(i + 1, total_points): # Avoid double counting (j > i)
                if abs(i - j) <= adjacency_window:
                    continue
                dist = distance.euclidean(coords[i], coords[j])
                if dist < proximity_threshold_meters:
                    hit_count += 1
                    
        return hit_count
    
    except Exception as e:
        print(f"Error counting proximity hits: {e}")
        return 0 # Return 0 on error

# Keep the alias for now, but we'll call the count function directly later
# check_buffer_self_intersection = count_self_proximity_hits 

def plot_trajectory(mmsi, traj_gs, classification, metrics, plot_filename):
    """Generates and saves a plot for a single trajectory."""
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        traj_gs.plot(ax=ax, linewidth=1.5, color='red')
        
        try:
            cx.add_basemap(ax, crs=traj_gs.crs.to_string(), source=cx.providers.OpenStreetMap.Mapnik, zoom='auto')
        except Exception as cx_err:
            print(f"  Warning: Could not add basemap for MMSI {mmsi}: {cx_err}")
            
        # Unpack metrics for title
        length_km = metrics.get('length_km', 0.0)
        avg_sog = metrics.get('avg_sog', np.nan)
        proximity_hits = metrics.get('proximity_hits', 0)
        
        title = (f"MMSI: {mmsi} - {classification}\n"+
                 f"Length: {length_km:.2f} km, Avg SOG: {avg_sog:.1f} kn, Hits: {proximity_hits}")
        ax.set_title(title)
        ax.set_axis_off()
        plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"MMSI: {mmsi} - Error during plotting: {e}")
        # Ensure plot is closed even if saving fails
        if 'fig' in locals() and plt.fignum_exists(fig.number):
             plt.close(fig)
        return False

def process_trajectories(trajectories, ais_df_subset, thresholds, plot_dirs):
    """Processes trajectories: calculates metrics, classifies, plots, and returns counts."""
    print("\n--- Filtering for Jitter & Identifying Potential Patterns for VLM ---")
    
    counts = {'jitter': 0, 'pattern_vlm': 0, 'no_prox': 0, 'processed': 0, 'plotted': 0}
    
    grouped_subset = ais_df_subset.groupby('MMSI')

    for mmsi, traj in trajectories.items():
        classification = "Other"
        plot_dir = None
        metrics = {}
        
        try:
            # --- Calculate Base Metrics --- 
            gs = gpd.GeoSeries([traj], crs='EPSG:4326')
            
            avg_sog = np.nan
            if 'SOG' in grouped_subset.get_group(mmsi).columns:
                 avg_sog = grouped_subset.get_group(mmsi)['SOG'].mean()
            else:
                print(f"  Warning: MMSI {mmsi} - SOG column missing.")
            metrics['avg_sog'] = avg_sog

            centroid = traj.centroid
            target_crs = 'EPSG:3857'
            if isinstance(centroid, Point) and not centroid.is_empty:
               try:
                   target_crs = estimate_utm_crs(centroid.y, centroid.x)
               except Exception:
                   pass 
            gs_projected = gs.to_crs(target_crs)
            projected_line = gs_projected.iloc[0]

            if not projected_line or projected_line.is_empty:
                 print(f"MMSI: {mmsi} - Could not project trajectory for metrics.")
                 continue
                 
            length_meters = projected_line.length
            metrics['length_km'] = length_meters / 1000.0
            minx, miny, maxx, maxy = projected_line.bounds
            metrics['bbox_width_m'] = maxx - minx
            metrics['bbox_height_m'] = maxy - miny
            metrics['proximity_hits'] = count_self_proximity_hits(traj)
            
            # --- Apply Simplified Filter Logic --- 
            is_likely_jitter = False
            if not np.isnan(metrics['avg_sog']): 
                if (metrics['avg_sog'] < thresholds['speed'] and 
                    metrics['bbox_width_m'] < thresholds['size'] and 
                    metrics['bbox_height_m'] < thresholds['size'] and 
                    metrics['proximity_hits'] > thresholds['hits']):
                    is_likely_jitter = True
                    classification = "Likely Jitter"
                    counts['jitter'] += 1
                    plot_dir = plot_dirs['jitter']
            
            # --- Classify based on proximity (if not jitter) --- 
            if not is_likely_jitter:
                if metrics['proximity_hits'] > 0:
                    # This is now our main candidate category for VLM
                    classification = "Potential Pattern for VLM" 
                    counts['pattern_vlm'] += 1 
                    plot_dir = plot_dirs['pattern'] # Use the 'pattern' directory
                else:
                     classification = "No Significant Proximity"
                     counts['no_prox'] += 1
                     plot_dir = plot_dirs['no_prox']
            
            # --- Print Results --- 
            print(f"MMSI: {mmsi} - Length: {metrics['length_km']:.2f} km, Avg SOG: {metrics['avg_sog']:.1f} knots, BBox: {metrics['bbox_width_m']:.0f}x{metrics['bbox_height_m']:.0f} m, Prox. Hits: {metrics['proximity_hits']} -> {classification}")

            # --- Plotting --- 
            if plot_dir:
                plot_filename = os.path.join(plot_dir, f"trajectory_{mmsi}.png")
                if plot_trajectory(mmsi, gs, classification, metrics, plot_filename):
                     counts['plotted'] += 1
                         
        except Exception as e:
            # Ensure MMSI is defined for the error message if it failed early
            mmsi_str = f"MMSI: {mmsi}" if 'mmsi' in locals() else "Unknown MMSI"
            print(f"{mmsi_str} - Error during processing loop: {e}")
            import traceback
            # traceback.print_exc() # Uncomment for detailed traceback
        
        counts['processed'] += 1 

    return counts

def print_summary(counts):
    """Prints the final summary counts."""
    print(f"\n---> Processed {counts.get('processed', 0)} trajectories.")
    print(f"---> Classified {counts.get('jitter', 0)} as Likely Jitter (saved to plots/likely_jitter).")
    print(f"---> Classified {counts.get('pattern_vlm', 0)} as Potential Patterns for VLM (saved to plots/potential_patterns).") 
    print(f"---> Classified {counts.get('no_prox', 0)} as No Significant Proximity (saved to plots/no_significant_proximity).")
    # print(f"---> Plotted {counts.get('plotted', 0)} trajectories.")

# --- Main execution block --- Refactored ---
if __name__ == "__main__":
    # --- Configuration --- 
    AIS_DATA_PATH = 'data/AIS_2024_01_01.csv' 
    BASE_PLOT_DIR = 'plots' 
    NUM_TEST_VESSELS = 100 
    RANDOM_SEED = 42 
    
    PLOT_DIRS = {
        'base': BASE_PLOT_DIR,
        'jitter': os.path.join(BASE_PLOT_DIR, 'likely_jitter'),
        'pattern': os.path.join(BASE_PLOT_DIR, 'potential_patterns'), 
        'no_prox': os.path.join(BASE_PLOT_DIR, 'no_significant_proximity')
    }
    
    THRESHOLDS = {
        'speed': 1.5, 
        'size': 500.0, 
        'hits': 50 
    }

    # --- Setup --- 
    for dir_path in PLOT_DIRS.values():
        if not os.path.exists(dir_path):
            print(f"Creating directory: {dir_path}")
            os.makedirs(dir_path)
    
    # --- Workflow --- 
    print("Starting trajectory processing...")
    ais_df = load_ais_data(AIS_DATA_PATH)

    if not ais_df.empty:
        # Calculate total unique MMSIs
        if 'MMSI' in ais_df.columns:
            total_unique_mmsis = ais_df['MMSI'].nunique()
            print(f"\nTotal unique MMSIs found in the dataset: {total_unique_mmsis}")
        else:
            print("\nError: MMSI column not found.")
            total_unique_mmsis = 0
        
        # Get testing subset 
        ais_df_subset = pd.DataFrame()
        if 'MMSI' in ais_df.columns and total_unique_mmsis > 0:
            unique_mmsis = ais_df['MMSI'].unique()
            if len(unique_mmsis) > NUM_TEST_VESSELS:
                 np.random.seed(RANDOM_SEED) 
                 test_mmsis = np.random.choice(unique_mmsis, size=NUM_TEST_VESSELS, replace=False)
                 print(f"\n--- TESTING MODE: Selecting {NUM_TEST_VESSELS} random vessels ---")
                 ais_df_subset = ais_df[ais_df['MMSI'].isin(test_mmsis)].copy()
            else:
                 print(f"\n--- TESTING MODE: Processing all {len(unique_mmsis)} vessels in dataset ---")
                 ais_df_subset = ais_df
        else: 
             print("\nError: Cannot create subset.")

        # Process if subset is valid
        if not ais_df_subset.empty:
            vessel_trajectories = create_trajectories(ais_df_subset, min_points=5) 

            if vessel_trajectories:
                print(f"\nSuccessfully created {len(vessel_trajectories)} vessel trajectories for processing.")
                results = process_trajectories(vessel_trajectories, ais_df_subset, THRESHOLDS, PLOT_DIRS)
                print_summary(results)
            else:
                 print("\nNo trajectories created from the subset.")
        else:
             print("\nSubset generation failed, cannot process trajectories.")
    else:
        print("\nData loading failed. Cannot proceed.")

    print("\nProcessing finished.") 