# natsec-hack-ais/reprocess_candidates.py
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import warnings
import matplotlib.pyplot as plt
import contextily as cx
import os
from pyproj import CRS
import numpy as np
from scipy.spatial import distance
import glob
import base64
import anthropic
import csv
import json
from datetime import datetime
import shutil

# Suppress warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)

# --- Helper Functions (Copied from process_survey_named_vessels.py) ---
# These are identical to the functions in the previous script

def load_ais_data(csv_path: str) -> pd.DataFrame:
    """Loads AIS data, parses timestamps, cleans, and sorts."""
    try:
        print(f"Loading AIS data from {csv_path}...")
        df = pd.read_csv(csv_path, low_memory=False)
        required_cols = ['MMSI', 'LAT', 'LON'] # BaseDateTime is optional for this input
        if not all(col in df.columns for col in required_cols):
             raise ValueError(f"CSV must contain columns: {required_cols}")
        
        print("Preprocessing data...")
        # Ensure BaseDateTime exists and handle conversion/missing
        if 'BaseDateTime' not in df.columns:
             print("Warning: BaseDateTime column missing, cannot sort by time.")
             df['BaseDateTime'] = pd.NaT
        else: 
             df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'], errors='coerce')

        df.dropna(subset=['LAT', 'LON', 'MMSI'], inplace=True)

        # Handle MMSI type (might be int or string depending on source)
        try:
            df['MMSI'] = df['MMSI'].astype(int)
        except ValueError:
             print("Warning: MMSI column contains non-integer values. Treating as string.")
             df['MMSI'] = df['MMSI'].astype(str)

        df = df[(df['LAT'] >= -90) & (df['LAT'] <= 90) & (df['LON'] >= -180) & (df['LON'] <= 180)]
        df = df.reset_index() # Keep original order via index

        print(f"Loaded and preprocessed {len(df)} data points.")
        return df
    except FileNotFoundError:
        print(f"Error: File not found at {csv_path}")
        return pd.DataFrame()
    except ValueError as ve:
        print(f"Error processing CSV: {ve}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return pd.DataFrame()

def create_trajectories(df: pd.DataFrame, min_points: int = 2) -> dict:
    """Converts AIS DataFrame points into LineString trajectories per MMSI."""
    print("Creating trajectories...")
    if df.empty: return {}
    trajectories = {}
    try:
        geometry = [Point(xy) for xy in zip(df['LON'], df['LAT'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
        grouped = gdf.groupby('MMSI')
        for mmsi, group in grouped:
            if len(group) >= min_points:
                # Sort by index (original order) as BaseDateTime might be missing/NaT
                group = group.sort_values(by='index')
                trajectory = LineString(group['geometry'].tolist())
                trajectories[mmsi] = trajectory
        print(f"Created {len(trajectories)} trajectories.")
        return trajectories
    except Exception as e:
        print(f"An unexpected error during trajectory creation: {e}")
        return {}

def estimate_utm_crs(lat, lon):
    """Estimates the UTM CRS based on a latitude and longitude."""
    return CRS.from_dict({
        'proj': 'utm', 'zone': int((lon + 180) / 6) + 1, 'south': lat < 0,
        'ellps': 'WGS84', 'datum': 'WGS84', 'units': 'm'
    })

def count_self_proximity_hits(trajectory: LineString, proximity_threshold_meters: float = 200.0) -> int:
    """Counts pairs of non-adjacent points within a threshold distance."""
    hit_count = 0
    if trajectory is None or trajectory.is_empty: return hit_count
    coords_list = list(trajectory.coords)
    if len(coords_list) < 5: return hit_count
    try:
        gs = gpd.GeoSeries([trajectory], crs='EPSG:4326')
        centroid = trajectory.centroid
        target_crs = 'EPSG:3857'
        if isinstance(centroid, Point) and not centroid.is_empty:
            try: target_crs = estimate_utm_crs(centroid.y, centroid.x)
            except Exception: pass
        gs_projected = gs.to_crs(target_crs)
        projected_line = gs_projected.iloc[0]
        if projected_line is None or projected_line.is_empty: return hit_count
        coords = np.array(projected_line.coords)
        total_points = len(coords)
        if total_points < 5: return hit_count
        adjacency_window = max(2, int(total_points * 0.1))
        for i in range(total_points):
            for j in range(i + 1, total_points):
                if abs(i - j) <= adjacency_window: continue
                dist = distance.euclidean(coords[i], coords[j])
                if dist < proximity_threshold_meters: hit_count += 1
        return hit_count
    except Exception as e:
        print(f"Error counting proximity hits: {e}")
        return 0

def plot_trajectory(mmsi, traj_gs, classification, metrics, plot_filename):
    """Generates and saves a plot for a single trajectory."""
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        traj_gs.plot(ax=ax, linewidth=1.5, color='red')
        try:
            cx.add_basemap(ax, crs=traj_gs.crs.to_string(), source=cx.providers.OpenStreetMap.Mapnik, zoom='auto')
        except Exception as cx_err:
            print(f"  Warning: Could not add basemap for MMSI {mmsi}: {cx_err}")
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
        if 'fig' in locals() and plt.fignum_exists(fig.number): plt.close(fig)
        return False

def encode_image_base64(image_path):
    """Encodes an image file to base64 for API transmission."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_trajectory_with_claude(image_path, mmsi, api_key=None):
    """Sends trajectory image to Claude API for hydrographic survey pattern analysis."""
    try:
        # Use provided API key or default to environment variable
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        base64_image = encode_image_base64(image_path)
        
        # Prompt text for Claude requesting JSON output
        prompt = """
        I need you to analyze this vessel trajectory plot and identify if it exhibits patterns consistent with a hydrographic survey.

        Hydrographic surveys are often characterized by systematic back-and-forth or "mowing the lawn" track lines over a defined area.
        This pattern is used when vessels systematically map the seafloor or conduct other survey activities.

        Key characteristics of hydrographic survey patterns include:
        - Systematic parallel or near-parallel track lines
        - Regular, tight turns connecting the track lines
        - Coverage of a defined geographic area
        - Often has a "lawn mower" pattern appearance

        Please analyze the trajectory in this image and determine if it shows characteristics consistent with a hydrographic survey pattern.
        
        YOU MUST respond with a JSON object with the following structure:
        {
            "classification": "LIKELY_SURVEY_PATTERN" or "POSSIBLE_SURVEY_PATTERN" or "UNLIKELY_SURVEY_PATTERN",
            "explanation": "Your explanation of why you made this classification in 1-3 sentences"
        }

        Where:
        - "LIKELY_SURVEY_PATTERN" means the trajectory clearly shows systematic back-and-forth patterns consistent with hydrographic survey operations
        - "POSSIBLE_SURVEY_PATTERN" means there are some survey-like features but the pattern is less definitive
        - "UNLIKELY_SURVEY_PATTERN" means the trajectory does not resemble a hydrographic survey pattern
        """

        # Create message with the image and prompt
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Updated model ID
            max_tokens=4096,  # Maximum tokens
            temperature=0,
            system="You analyze vessel trajectory patterns to identify hydrographic survey activities. Always respond in valid JSON format with the requested structure.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Return Claude's analysis
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Error analyzing trajectory with Claude: {e}")
        return f"ERROR: {str(e)}"

def extract_classification(vlm_result):
    """Extracts just the classification from the VLM JSON result."""
    try:
        # Try to parse the result as JSON
        result_json = json.loads(vlm_result)
        return result_json.get("classification", "UNKNOWN")
    except json.JSONDecodeError:
        # If not valid JSON, return the raw result
        print(f"Warning: Could not parse VLM result as JSON: {vlm_result}")
        return "PARSING_ERROR"
    except Exception as e:
        print(f"Error extracting classification: {e}")
        return "ERROR"

def process_trajectories(trajectories, ais_df_subset, thresholds, plot_dirs, claude_api_key=None):
    """Processes trajectories: calculates metrics, classifies, plots, and returns counts AND candidate MMSIs."""
    print("\n--- Re-Filtering Candidate Set for Jitter & Potential Patterns ---") # Updated title
    counts = {'jitter': 0, 'pattern_vlm': 0, 'no_prox': 0, 'processed': 0, 'plotted': 0,
              'likely_survey': 0, 'possible_survey': 0}  # Added counts for new categories
    pattern_mmsis = [] # Still useful to know which ones passed this stage
    pattern_info = [] # To store pattern VLM analysis results
    grouped_subset = ais_df_subset.groupby('MMSI')
    for mmsi, traj in trajectories.items():
        classification = "Other"
        plot_dir = None
        metrics = {}
        try:
            # --- Calculate Base Metrics ---
            gs = gpd.GeoSeries([traj], crs='EPSG:4326')
            avg_sog = np.nan
            mmsi_group = grouped_subset.get_group(mmsi)
            # Check if SOG exists in this specific CSV
            if 'SOG' in mmsi_group.columns:
                 avg_sog = mmsi_group['SOG'].mean() # Pandas mean ignores NaN
            else: print(f"  Warning: MMSI {mmsi} - SOG column missing in input CSV.")
            metrics['avg_sog'] = avg_sog # Will be NaN if SOG was missing

            centroid = traj.centroid
            target_crs = 'EPSG:3857'
            if isinstance(centroid, Point) and not centroid.is_empty:
               try: target_crs = estimate_utm_crs(centroid.y, centroid.x)
               except Exception: pass 
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
            # Check if avg_sog is NaN before comparing
            if not pd.isna(metrics['avg_sog']): 
                if (metrics['avg_sog'] < thresholds['speed'] and
                    metrics['bbox_width_m'] < thresholds['size'] and
                    metrics['bbox_height_m'] < thresholds['size'] and
                    metrics['proximity_hits'] > thresholds['hits']):
                    is_likely_jitter = True
                    classification = "Likely Jitter"
                    counts['jitter'] += 1
                    plot_dir = plot_dirs['jitter']
            elif metrics['bbox_width_m'] < thresholds['size'] and \
                 metrics['bbox_height_m'] < thresholds['size'] and \
                 metrics['proximity_hits'] > thresholds['hits']:
                 # If SOG is missing but size is small and hits are high, still likely jitter
                 is_likely_jitter = True
                 classification = "Likely Jitter (No SOG)"
                 counts['jitter'] += 1
                 plot_dir = plot_dirs['jitter']

            # --- Classify based on proximity (if not jitter) ---
            if not is_likely_jitter:
                if metrics['proximity_hits'] > 0:
                    classification = "Potential Pattern for VLM"
                    counts['pattern_vlm'] += 1
                    pattern_mmsis.append(mmsi) # Add to list
                    plot_dir = plot_dirs['pattern']
                else:
                     classification = "No Significant Proximity"
                     counts['no_prox'] += 1
                     plot_dir = plot_dirs['no_prox']
            # --- Print Results ---
            print(f"MMSI: {mmsi} - Length: {metrics['length_km']:.2f} km, Avg SOG: {metrics['avg_sog']:.1f} knots, BBox: {metrics['bbox_width_m']:.0f}x{metrics['bbox_height_m']:.0f} m, Prox. Hits: {metrics['proximity_hits']} -> {classification}")
            # --- Plotting ---
            if plot_dir:
                # Adjust plot directory based on re-classification
                plot_filename = os.path.join(plot_dir, f"trajectory_{mmsi}.png")
                if plot_trajectory(mmsi, gs, classification, metrics, plot_filename):
                     counts['plotted'] += 1
                     
                     # For potential patterns, send to Claude VLM for analysis
                     if classification == "Potential Pattern for VLM":
                         print(f"MMSI {mmsi} - Sending to Claude VLM for analysis...")
                         vlm_result = analyze_trajectory_with_claude(plot_filename, mmsi, api_key=claude_api_key)
                         print(f"MMSI {mmsi} - Claude VLM result: {vlm_result}")
                         
                         # Extract just the classification from the JSON result
                         survey_classification = extract_classification(vlm_result)
                         
                         # Save the result with the trajectory info
                         pattern_info.append({
                             'mmsi': mmsi,
                             'length_km': metrics['length_km'],
                             'avg_sog': metrics['avg_sog'],
                             'prox_hits': metrics['proximity_hits'],
                             'bbox_width_m': metrics['bbox_width_m'],
                             'bbox_height_m': metrics['bbox_height_m'],
                             'survey_classification': survey_classification,
                             'vlm_raw_result': vlm_result
                         })
                         
                         # Copy the plot to the appropriate survey classification folder if applicable
                         if survey_classification == "LIKELY_SURVEY_PATTERN":
                             likely_survey_filename = os.path.join(plot_dirs['likely_survey'], f"trajectory_{mmsi}.png")
                             shutil.copy2(plot_filename, likely_survey_filename)
                             counts['likely_survey'] += 1
                             print(f"MMSI {mmsi} - Copied to likely survey patterns folder")
                         elif survey_classification == "POSSIBLE_SURVEY_PATTERN":
                             possible_survey_filename = os.path.join(plot_dirs['possible_survey'], f"trajectory_{mmsi}.png")
                             shutil.copy2(plot_filename, possible_survey_filename)
                             counts['possible_survey'] += 1
                             print(f"MMSI {mmsi} - Copied to possible survey patterns folder")
        except Exception as e:
            mmsi_str = f"MMSI: {mmsi}" if 'mmsi' in locals() else "Unknown MMSI"
            print(f"{mmsi_str} - Error during processing loop: {e}")
            # import traceback
            # traceback.print_exc()
        counts['processed'] += 1
    return counts, pattern_mmsis, pattern_info

def print_summary(counts):
    """Prints the final summary counts."""
    print(f"\n---> Processed {counts.get('processed', 0)} trajectories.")
    print(f"---> Classified {counts.get('jitter', 0)} as Likely Jitter (saved to plots/likely_jitter).")
    print(f"---> Classified {counts.get('pattern_vlm', 0)} as Potential Patterns for VLM (saved to plots/potential_patterns).")
    print(f"---> Classified {counts.get('no_prox', 0)} as No Significant Proximity (saved to plots/no_significant_proximity).")
    # print(f"---> Plotted {counts.get('plotted', 0)} trajectories.")

def save_vlm_results(pattern_info, output_path):
    """Saves VLM analysis results to a CSV file."""
    if not pattern_info:
        print("No pattern information to save.")
        return
        
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_path, f"vlm_analysis_results_{timestamp}.csv")
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['mmsi', 'length_km', 'avg_sog', 'prox_hits', 'bbox_width_m', 'bbox_height_m', 'survey_classification']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for info in pattern_info:
                # Create a new dict with just the fields we want in the CSV
                row = {k: info[k] for k in fieldnames if k in info}
                writer.writerow(row)
                
        print(f"VLM analysis results saved to {filename}")
        
        # Also save full results including raw VLM output to a separate file
        full_filename = os.path.join(output_path, f"vlm_analysis_full_{timestamp}.csv")
        with open(full_filename, 'w', newline='') as csvfile:
            fieldnames = ['mmsi', 'length_km', 'avg_sog', 'prox_hits', 'bbox_width_m', 'bbox_height_m', 'survey_classification', 'vlm_raw_result']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for info in pattern_info:
                writer.writerow(info)
                
        print(f"Full VLM analysis results (including raw output) saved to {full_filename}")
    except Exception as e:
        print(f"Error saving VLM results: {e}")

# --- Main execution block --- Reprocessing Candidates ---
if __name__ == "__main__":
    # Current directory (where vlm_processing.py is located)
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # --- Configuration ---
    # Use data directory within filter_vlm_processing folder
    CANDIDATE_DATA_PATH = os.path.join(CURRENT_DIR, 'data/combined_candidates.csv')
    
    # Use plots directory within filter_vlm_processing folder
    BASE_PLOT_DIR = os.path.join(CURRENT_DIR, 'plots')
    
    # Define PLOT_DIRS using the new base
    PLOT_DIRS = {
        'base': BASE_PLOT_DIR,
        'jitter': os.path.join(BASE_PLOT_DIR, 'likely_jitter'),
        'pattern': os.path.join(BASE_PLOT_DIR, 'potential_patterns'),
        'no_prox': os.path.join(BASE_PLOT_DIR, 'no_significant_proximity'),
        # Add new folders for LIKELY and POSSIBLE survey patterns
        'likely_survey': os.path.join(BASE_PLOT_DIR, 'likely_survey_pattern'),
        'possible_survey': os.path.join(BASE_PLOT_DIR, 'possible_survey_pattern')
    }
    # Use the same thresholds as before
    THRESHOLDS = {
        'speed': 1.5, 'size': 500.0, 'hits': 50
    }
    
    # Claude API configuration - either set this directly or use environment variable
    # If using environment variable, set ANTHROPIC_API_KEY in your environment
    CLAUDE_API_KEY = "Your Anthropic API key here"  # Set to your API key string if not using environment variable

    # --- Setup ---
    for dir_path in PLOT_DIRS.values():
        if not os.path.exists(dir_path):
            print(f"Creating directory: {dir_path}")
            os.makedirs(dir_path)

    # --- Workflow ---
    print(f"Starting reprocessing of candidate trajectories from {CANDIDATE_DATA_PATH}...")
    candidate_df = load_ais_data(CANDIDATE_DATA_PATH) # Use the same loading function

    if not candidate_df.empty:
        # No filtering needed, just create trajectories
        vessel_trajectories = create_trajectories(candidate_df, min_points=5)

        if vessel_trajectories:
            print(f"\nSuccessfully created {len(vessel_trajectories)} trajectories from candidate data.")
            # Process, classify, and plot (we don't need to save candidates again)
            results, _, pattern_info = process_trajectories(vessel_trajectories, candidate_df, THRESHOLDS, PLOT_DIRS, claude_api_key=CLAUDE_API_KEY)
            print_summary(results)
            
            # Save VLM analysis results
            if pattern_info:
                save_vlm_results(pattern_info, PLOT_DIRS['base'])
        else:
             print("\nNo trajectories created from the candidate data.")
    else:
        print("\nLoading candidate data failed. Cannot plot.")

    print("\nReprocessing finished.") 