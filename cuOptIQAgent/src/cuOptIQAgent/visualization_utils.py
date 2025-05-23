import os
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
import base64

def visualize_factory_state(state: Any, output_dir: str = "optimization_results", filename_prefix: str = "optimization"):
    """Creates visualizations for the factory state"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate visualizations only if we have a solution
    if state.solution and 'vehicle_data' in state.solution:
        # Create route network visualizations for each forklift
        create_route_networks(state, output_dir, filename_prefix)
        
        # Create Gantt chart for task scheduling
        create_gantt_chart(state, output_dir, filename_prefix)

def create_route_networks(state: Any, output_dir: str, filename_prefix: str):
    """Creates network visualizations for each forklift route"""
    try:
        # Location mapping for labels
        location_map = {
            0: "Depot",
            1: "Insulation",
            2: "Weather Stripping",
            3: "Fiber Glass",
            4: "Shingles",
            5: "Truck 1",
            6: "Truck 2",
            7: "Truck 3",
            8: "Truck 4"
        }
        
        # Location coordinates for improved visualization layout
        # Storage locations in a row at the top, trucks at the bottom, depot on left
        location_coords = {
            0: (-2, 0),     # Depot on the left
            # Storage locations in a row at the top
            1: (0, 2),      # Insulation
            2: (2, 2),      # Weather Stripping
            3: (4, 2),      # Fiber Glass
            4: (6, 2),      # Shingles
            # Trucks in a row at the bottom
            5: (0, -2),     # Truck 1
            6: (2, -2),     # Truck 2
            7: (4, -2),     # Truck 3
            8: (6, -2)      # Truck 4
        }
        
        # Location type colors - these are for the LOCATIONS, not activities
        location_type_colors = {
            'depot': '#FFCC99',      # Light orange for depot
            'pickup': '#CCFFCC',     # Light green for pickup locations (storage)
            'delivery': '#CCCCFF'    # Light blue for delivery locations (trucks)
        }
        
        # Process each vehicle's route
        vehicle_data = state.solution.get('vehicle_data', {})
        
        for vehicle_id, data in vehicle_data.items():
            try:
                # Create a directed graph
                G = nx.DiGraph()
                
                # Get route and activity types
                route = data.get('route', [])
                activity_types = data.get('type', [])
                
                # Skip if no route
                if not route:
                    continue
                
                # Filter out wait activities
                filtered_route = []
                filtered_activities = []
                
                for i, (location, activity) in enumerate(zip(route, activity_types)):
                    if activity != 'w':  # Skip wait activities
                        filtered_route.append(location)
                        filtered_activities.append(activity)
                
                # Skip if no activities left after filtering
                if not filtered_route:
                    continue
                
                # Add nodes with labels
                for i, location in enumerate(filtered_route):
                    activity = filtered_activities[i]
                    
                    # Determine the activity label based on the activity type
                    if activity == 'p' or activity == 'Pickup':
                        activity_label = 'Pickup'
                    elif activity == 'd' or activity == 'Delivery':
                        activity_label = 'Delivery'
                    elif activity == 'Depot':
                        activity_label = 'Depot'
                    else:
                        activity_label = activity  # Use as-is if unknown
                    
                    # Add node with location and activity info
                    G.add_node(
                        i, 
                        pos=location_coords[location],
                        label=f"{location_map[location]}\n({activity_label})",
                        location=location,
                        activity=activity_label
                    )
                
                # Add edges between consecutive locations
                for i in range(len(filtered_route) - 1):
                    G.add_edge(i, i + 1)
                
                # Create fresh figure with fixed size
                plt.close('all')  # Close any existing figures
                fig = plt.figure(figsize=(12, 8), constrained_layout=False)
                ax = fig.add_subplot(111)
                
                # Get node positions
                pos = nx.get_node_attributes(G, 'pos')
                
                # Draw nodes with different colors based on location type
                node_colors = []
                for i, location in enumerate(filtered_route):
                    if location == 0:
                        node_colors.append(location_type_colors['depot'])
                    elif 1 <= location <= 4:
                        node_colors.append(location_type_colors['pickup'])
                    else:  # 5-8 are delivery locations
                        node_colors.append(location_type_colors['delivery'])
                
                # Draw nodes with larger size
                nx.draw_networkx_nodes(
                    G, pos, 
                    node_size=3000, 
                    node_color=node_colors,
                    edgecolors='black',
                    linewidths=2,
                    ax=ax
                )
                
                # Draw edges with arrows
                nx.draw_networkx_edges(
                    G, pos, 
                    width=2, 
                    arrowsize=25, 
                    edge_color='gray',
                    arrows=True,
                    connectionstyle='arc3,rad=0.1',  # Curved edges
                    ax=ax
                )
                
                # Draw labels with better font
                nx.draw_networkx_labels(
                    G, pos, 
                    labels={n: G.nodes[n]['label'] for n in G.nodes()},
                    font_size=11,
                    font_weight='bold',
                    font_family='sans-serif',
                    ax=ax
                )
                
                # Add background shapes to highlight areas
                # Storage area (light yellow rectangle)
                storage_rect = plt.Rectangle((-1, 1), 8, 2, color='lightyellow', alpha=0.3, zorder=-1)
                ax.add_patch(storage_rect)
                ax.text(3, 3.2, 'Storage Area', fontsize=14, ha='center', fontweight='bold')
                
                # Truck area (light blue rectangle)
                truck_rect = plt.Rectangle((-1, -3), 8, 2, color='lightcyan', alpha=0.3, zorder=-1)
                ax.add_patch(truck_rect)
                ax.text(3, -3.2, 'Loading Area', fontsize=14, ha='center', fontweight='bold')
                
                # Depot area (light green circle)
                depot_circle = plt.Circle((-2, 0), 1.2, color='lightsalmon', alpha=0.2, zorder=-1)
                ax.add_patch(depot_circle)
                
                # Add title and turn off axis
                ax.set_title(f"Forklift {int(vehicle_id) + 1} Route", fontsize=16)
                ax.axis('off')
                
                # Set fixed axis limits for ALL forklift visualizations
                ax.set_xlim(-4, 8)
                ax.set_ylim(-4, 4)
                
                # Add legend for location types
                legend_elements = [
                    plt.Rectangle((0, 0), 1, 1, facecolor=location_type_colors['depot'], edgecolor='black', label='Depot'),
                    plt.Rectangle((0, 0), 1, 1, facecolor=location_type_colors['pickup'], edgecolor='black', label='Storage Location'),
                    plt.Rectangle((0, 0), 1, 1, facecolor=location_type_colors['delivery'], edgecolor='black', label='Truck Location')
                ]
                ax.legend(handles=legend_elements, loc='lower right')
                
                # Apply consistent margins and spacing
                plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
                
                # Save the figure with explicit parameters
                output_path = os.path.join(output_dir, f"{filename_prefix}_network_forklift_{int(vehicle_id) + 1}.png")
                fig.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.5)
                plt.close(fig)
            except Exception as e:
                print(f"Error creating visualization for vehicle {vehicle_id}: {str(e)}")
                continue
    except Exception as e:
        print(f"Error in create_route_networks: {str(e)}")

def create_gantt_chart(state: Any, output_dir: str, filename_prefix: str):
    """Creates a Gantt chart visualization of the schedule"""
    try:
        # Location mapping for labels
        location_map = {
            0: "Depot",
            1: "Insulation",
            2: "Weather Stripping",
            3: "Fiber Glass",
            4: "Shingles",
            5: "Truck 1",
            6: "Truck 2",
            7: "Truck 3",
            8: "Truck 4"
        }
        
        # Activity type mapping
        activity_map = {
            'p': 'PU',
            'd': 'DL',
            'Pickup': 'PU',
            'Delivery': 'DL',
            'Depot': 'At'
        }
        
        # Activity colors
        activity_colors = {
            'p': '#90EE90',  # Light green
            'd': '#ADD8E6',  # Light blue
            'Pickup': '#90EE90',  # Light green
            'Delivery': '#ADD8E6',  # Light blue
            'Depot': '#FFCC99'  # Light orange
        }
        
        # Create figure
        plt.figure(figsize=(14, 8))
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Process each vehicle's schedule
        vehicle_data = state.solution.get('vehicle_data', {})
        
        # Sort vehicles by ID for consistent display
        vehicle_ids = sorted(vehicle_data.keys(), key=lambda x: int(x))
        
        y_labels = []
        y_ticks = []
        
        # Track the maximum time for setting x-axis limits
        max_time = 1  # Start with a minimum value
        
        # Process each vehicle
        for vehicle_idx, vehicle_id in enumerate(vehicle_ids):
            data = vehicle_data[vehicle_id]
            
            try:
                y_pos = len(vehicle_ids) - vehicle_idx
                y_labels.append(f"Forklift {int(vehicle_id) + 1}")
                y_ticks.append(y_pos)
                
                # Get route, arrival times, and activity types
                route = data.get('route', [])
                
                # Check if we have arrival_stamp (from example) or arrival_times
                arrival_times = data.get('arrival_stamp', data.get('arrival_times', []))
                
                # Check if we have type or activity_types
                activity_types = data.get('type', [])
                
                # Skip if no route or missing data
                if not route or not arrival_times or not activity_types:
                    continue
                
                # Filter out wait activities
                filtered_indices = []
                for i, activity in enumerate(activity_types):
                    if activity != 'w' and i < len(route) and i < len(arrival_times):
                        filtered_indices.append(i)
                
                if not filtered_indices:
                    continue
                
                # Create filtered lists
                filtered_route = [route[i] for i in filtered_indices]
                filtered_arrival_times = [arrival_times[i] for i in filtered_indices]
                filtered_activity_types = [activity_types[i] for i in filtered_indices]
                
                # Calculate service times (time spent at each location)
                filtered_service_times = []
                for i in range(len(filtered_indices)):
                    idx = filtered_indices[i]
                    if idx + 1 < len(arrival_times):
                        # Service time is the difference between this arrival and the next
                        next_idx = filtered_indices[i + 1] if i + 1 < len(filtered_indices) else idx + 1
                        service_time = arrival_times[next_idx] - arrival_times[idx]
                        # Ensure minimum service time
                        filtered_service_times.append(max(1, service_time))
                    else:
                        # For the last activity, use a default service time
                        filtered_service_times.append(2)
                
                # Plot each activity as a bar
                for i in range(len(filtered_route)):
                    location = filtered_route[i]
                    activity = filtered_activity_types[i]
                    start_time = filtered_arrival_times[i]
                    
                    # For the last activity, use a fixed service time
                    duration = filtered_service_times[i] if i < len(filtered_service_times) else 2
                    
                    # Update max time
                    max_time = max(max_time, start_time + duration)
                    
                    # Create activity label
                    activity_label = f"{activity_map.get(activity, 'At')} {location_map.get(location, f'Location {location}')}"
                    
                    # Plot the activity bar
                    bar = ax.barh(
                        y_pos,
                        duration,
                        left=start_time,
                        height=0.5,
                        color=activity_colors.get(activity, '#CCCCCC'),
                        edgecolor='black',
                        alpha=0.8
                    )
                    
                    # Add text label if the bar is wide enough
                    if duration > 1:  # Only label bars that are at least 1 time unit
                        ax.text(
                            start_time + duration/2,
                            y_pos,
                            activity_label,
                            ha='center',
                            va='center',
                            fontsize=9,
                            fontweight='bold'
                        )
                    
                    # Add connecting lines between activities
                    if i > 0:
                        prev_end = filtered_arrival_times[i-1] + filtered_service_times[i-1] if i-1 < len(filtered_service_times) else filtered_arrival_times[i-1] + 2
                        if start_time > prev_end:
                            # Draw a dashed line for travel time
                            ax.plot(
                                [prev_end, start_time],
                                [y_pos, y_pos],
                                'k--',
                                alpha=0.5,
                                linewidth=1.5
                            )
                            
                            # Add travel time label
                            travel_time = start_time - prev_end
                            if travel_time > 1:  # Only label if travel time is significant
                                ax.text(
                                    prev_end + travel_time/2,
                                    y_pos + 0.25,
                                    f"Travel: {travel_time:.1f}",
                                    ha='center',
                                    va='bottom',
                                    fontsize=8,
                                    alpha=0.7
                                )
            except Exception as e:
                print(f"Error creating Gantt chart for vehicle {vehicle_id}: {str(e)}")
                continue
        
        # Add dummy data if no valid activities were found
        if max_time <= 1:
            max_time = 30  # Default time range
            # Add a note about missing data
            ax.text(
                max_time/2, 
                len(vehicle_ids)/2, 
                "No valid schedule data available",
                ha='center',
                va='center',
                fontsize=14,
                color='red',
                alpha=0.7
            )
        
        # Set chart properties
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_title('Forklift Schedule', fontsize=16)
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        
        # Set x-axis limits with some padding
        ax.set_xlim(0, max_time * 1.1)
        
        # Add legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=activity_colors['Pickup'], edgecolor='black', label='Pickup'),
            plt.Rectangle((0, 0), 1, 1, facecolor=activity_colors['Delivery'], edgecolor='black', label='Delivery'),
            plt.Rectangle((0, 0), 1, 1, facecolor=activity_colors['Depot'], edgecolor='black', label='Depot'),
            plt.Line2D([0], [0], color='k', linestyle='--', label='Travel')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Add background color to alternate rows for better readability
        for i, y_pos in enumerate(y_ticks):
            if i % 2 == 0:
                ax.axhspan(y_pos - 0.4, y_pos + 0.4, color='whitesmoke', zorder=-1)
        
        # Add grid lines for better time reference
        ax.xaxis.set_major_locator(plt.MultipleLocator(max(1, max_time // 10)))
        ax.xaxis.set_minor_locator(plt.MultipleLocator(max(0.5, max_time // 20)))
        ax.grid(which='minor', alpha=0.2)
        
        # Improve overall style
        plt.tight_layout()
        
        # Save the figure
        output_path = os.path.join(output_dir, f"{filename_prefix}_gantt.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)  # Close both figure instances
    except Exception as e:
        print(f"Error in create_gantt_chart: {str(e)}")

def get_visualization_markdown(output_dir: str, timestamp: str) -> str:
    """Creates markdown with embedded visualizations for UI display"""
    visualization_markdown = "\n\n### Visualizations\n\n"
    visualization_paths = []
    
    # Find all visualization files for this timestamp
    for filename in os.listdir(output_dir):
        if filename.startswith(f"optimization_{timestamp}") and filename.endswith(".png"):
            visualization_paths.append(os.path.join(output_dir, filename))
    
    if not visualization_paths:
        return ""
    
    # Add Gantt chart first if it exists
    gantt_path = next((path for path in visualization_paths if "gantt" in path), None)
    if gantt_path:
        with open(gantt_path, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode("utf-8")
            visualization_markdown += f"#### Forklift Schedule (Gantt Chart)\n\n"
            visualization_markdown += f"![Gantt Chart](data:image/png;base64,{base64_image})\n\n"
    
    # Then add route networks
    route_paths = [path for path in visualization_paths if "network_forklift" in path]
    route_paths.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))  # Sort by forklift number
    
    if route_paths:
        visualization_markdown += f"#### Forklift Routes\n\n"
        for path in route_paths:
            forklift_num = path.split("_")[-1].split(".")[0]
            with open(path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                visualization_markdown += f"**Forklift {forklift_num}**\n\n"
                visualization_markdown += f"![Forklift {forklift_num} Route](data:image/png;base64,{base64_image})\n\n"
    
    return visualization_markdown