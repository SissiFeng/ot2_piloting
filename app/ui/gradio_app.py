import gradio as gr
import asyncio
from typing import Dict, Any, Optional
from ..core.auth.auth_manager import AuthManager, UserRole
from ..core.workflow.experiment_flow import run_experiment
from ..core.storage.db_manager import DatabaseManager
from ..core.analysis.experiment_analyzer import ExperimentAnalyzer
from ..core.ml.experiment_optimizer import ExperimentOptimizer
import pandas as pd
import plotly.express as px
import json
import numpy as np

class EnhancedGradioUI:
    """Enhanced Gradio UI for experiment control and monitoring."""
    
    def __init__(self, auth_manager: AuthManager, db_manager: DatabaseManager):
        """Initialize UI with required managers."""
        self.auth_manager = auth_manager
        self.db_manager = db_manager
        self.analyzer = ExperimentAnalyzer()
        self.optimizer = ExperimentOptimizer(db_manager)
        self.current_user = None
        
    def create_interface(self):
        """Create enhanced Gradio interface."""
        
        # Authentication block
        with gr.Blocks(theme=gr.themes.Soft()) as app:
            gr.Markdown("# OT-2 Color Mixing Experiment System")
            
            # Login section
            with gr.Tab("Login"):
                with gr.Row():
                    email_input = gr.Textbox(label="Email")
                    password_input = gr.Textbox(label="Password", type="password")
                login_button = gr.Button("Login")
                login_status = gr.Markdown("Please login to continue")
            
            # Main experiment interface
            with gr.Tab("Experiment Control", visible=False) as experiment_tab:
                with gr.Row():
                    # Mode selection
                    mode_select = gr.Radio(
                        choices=["Manual", "Optimization"],
                        value="Manual",
                        label="Operation Mode"
                    )
                
                with gr.Row():
                    # Color mixing controls
                    with gr.Column():
                        gr.Markdown("### Color Mixing Parameters")
                        # Manual controls
                        with gr.Column(visible=True) as manual_controls:
                            red_slider = gr.Slider(0, 100, value=0, label="Red (%)")
                            yellow_slider = gr.Slider(0, 100, value=0, label="Yellow (%)")
                            blue_slider = gr.Slider(0, 100, value=0, label="Blue (%)")
                        
                        # Optimization controls
                        with gr.Column(visible=False) as optimization_controls:
                            gr.Markdown("### Optimization Settings")
                            target_spectrum = gr.File(label="Target Spectrum (Optional)")
                            max_iterations = gr.Slider(5, 50, value=20, label="Max Iterations")
                            convergence_threshold = gr.Slider(0.001, 0.1, value=0.01, label="Convergence Threshold")
                            
                            # Optimization status
                            optimization_status = gr.Markdown("Not started")
                            suggested_params = gr.JSON(label="Suggested Parameters")
                            convergence_plot = gr.Plot(label="Optimization Progress")
                        
                        total_volume = gr.Number(label="Total Volume (µL)", value=300)
                        well_select = gr.Dropdown(
                            choices=["A1", "A2", "A3", "B1", "B2", "B3"],
                            label="Target Well"
                        )
                        
                        # Preview section
                        gr.Markdown("### Preview")
                        color_preview = gr.Plot(label="Color Distribution")
                        volume_info = gr.JSON(label="Volume Information")
                    
                    # Real-time monitoring
                    with gr.Column():
                        gr.Markdown("### Experiment Status")
                        status_info = gr.Markdown("Ready")
                        progress_bar = gr.Progress()
                        spectrum_plot = gr.Plot(label="Real-time Spectrum")
                
                # Control buttons
                with gr.Row():
                    start_button = gr.Button("Start Experiment", variant="primary")
                    stop_button = gr.Button("Stop", variant="stop")
                    reset_button = gr.Button("Reset")
                    
                    # Optimization specific buttons
                    with gr.Column(visible=False) as opt_buttons:
                        next_exp_button = gr.Button("Run Next Experiment")
                        finish_opt_button = gr.Button("Finish Optimization")

            # Analysis interface
            with gr.Tab("Data Analysis", visible=False) as analysis_tab:
                with gr.Row():
                    # Experiment selection
                    with gr.Column():
                        gr.Markdown("### Experiment Selection")
                        experiment_dropdown = gr.Dropdown(
                            choices=[],
                            label="Select Experiment"
                        )
                        refresh_button = gr.Button("Refresh")
                    
                    # Analysis results
                    with gr.Column():
                        gr.Markdown("### Analysis Results")
                        analysis_plots = gr.Plot(label="Spectral Analysis")
                        statistics_display = gr.JSON(label="Statistical Metrics")
                        download_report = gr.Button("Generate Report")
            
            # Admin interface
            with gr.Tab("Admin", visible=False) as admin_tab:
                with gr.Row():
                    gr.Markdown("### System Status")
                    system_metrics = gr.JSON(label="System Metrics")
                    user_stats = gr.DataFrame(label="User Statistics")
            
            # Login handler
            async def login(email: str, password: str):
                user = await self.auth_manager.authenticate_user(
                    self.db_manager, email, password
                )
                if user:
                    self.current_user = user
                    experiment_tab.visible = True
                    analysis_tab.visible = True
                    admin_tab.visible = user.role == UserRole.ADMIN
                    return "Login successful! Welcome, " + user.email
                return "Login failed. Please check your credentials."
            
            login_button.click(
                login,
                inputs=[email_input, password_input],
                outputs=[login_status]
            )
            
            # Color preview handler
            def update_preview(r: float, y: float, b: float):
                # Create a simple color visualization
                fig = px.pie(
                    values=[r, y, b],
                    names=['Red', 'Yellow', 'Blue'],
                    title='Color Distribution'
                )
                volumes = {
                    'red': r,
                    'yellow': y,
                    'blue': b,
                    'total': r + y + b
                }
                return fig, volumes
            
            # Update preview on slider changes
            for slider in [red_slider, yellow_slider, blue_slider]:
                slider.change(
                    update_preview,
                    inputs=[red_slider, yellow_slider, blue_slider],
                    outputs=[color_preview, volume_info]
                )
            
            # Mode selection handler
            def update_mode(mode):
                return (
                    mode == "Manual",  # manual_controls visibility
                    mode == "Optimization",  # optimization_controls visibility
                    mode == "Optimization"  # opt_buttons visibility
                )
            
            mode_select.change(
                update_mode,
                inputs=[mode_select],
                outputs=[manual_controls, optimization_controls, opt_buttons]
            )
            
            # Optimization handlers
            async def start_optimization(target_file, max_iter, threshold):
                if not self.current_user:
                    return "Please login first", None, None
                
                try:
                    # Initialize optimization
                    target_data = np.loadtxt(target_file.name) if target_file else None
                    analysis = await self.optimizer.initialize_optimization(
                        None,  # Will create new experiment
                        target_data,
                        {
                            "max_iterations": max_iter,
                            "convergence_threshold": threshold,
                            "total_volume": 300  # Fixed for now
                        }
                    )
                    
                    # Get first suggestion
                    status = await self.optimizer.get_optimization_status(analysis.id)
                    
                    return (
                        f"Optimization initialized. Experiment {1}/{max_iter}",
                        status["suggested_params"],
                        status["convergence_plot"]
                    )
                    
                except Exception as e:
                    return f"Error: {str(e)}", None, None
            
            async def run_next_experiment(suggested_params, well):
                if not suggested_params:
                    return "No parameters suggested", None, None
                
                try:
                    # Run experiment with suggested parameters
                    result = await run_experiment(
                        self.db_manager,
                        {
                            "volumes": suggested_params,
                            "well_id": well,
                            "user_id": str(self.current_user.id)
                        }
                    )
                    
                    # Update optimizer with results
                    status = await self.optimizer.update_model(result)
                    
                    return (
                        f"Experiment completed. {status['current_iteration']}/{status['max_iterations']}",
                        status["suggested_params"],
                        status["convergence_plot"]
                    )
                    
                except Exception as e:
                    return f"Error: {str(e)}", None, None
            
            # Connect optimization handlers
            start_button.click(
                start_optimization,
                inputs=[target_spectrum, max_iterations, convergence_threshold],
                outputs=[optimization_status, suggested_params, convergence_plot],
                show_progress=True
            )
            
            next_exp_button.click(
                run_next_experiment,
                inputs=[suggested_params, well_select],
                outputs=[optimization_status, suggested_params, convergence_plot],
                show_progress=True
            )
            
            # Experiment handler
            async def run_experiment_handler(r: float, y: float, b: float, well: str):
                if not self.current_user:
                    return "Please login first"
                
                try:
                    # Prepare experiment parameters
                    params = {
                        "volumes": {
                            "red": r,
                            "yellow": y,
                            "blue": b
                        },
                        "well_id": well,
                        "user_id": str(self.current_user.id)
                    }
                    
                    # Run experiment
                    result = await run_experiment(self.db_manager, params)
                    
                    # Analyze results
                    analysis = await self.analyzer.analyze_results(result)
                    
                    # Update UI
                    return (
                        "Experiment completed successfully",
                        analysis["plots"]["spectrum_plot"],
                        analysis["statistical_analysis"]
                    )
                    
                except Exception as e:
                    return f"Error: {str(e)}", None, None
            
            start_button.click(
                run_experiment_handler,
                inputs=[red_slider, yellow_slider, blue_slider, well_select],
                outputs=[status_info, spectrum_plot, statistics_display]
            )
            
            # Analysis handlers
            async def load_history():
                if not self.current_user:
                    return [], None
                
                experiments = await self.db_manager.get_user_experiments(
                    self.current_user.email
                )
                return [str(exp["id"]) for exp in experiments], None
            
            refresh_button.click(
                load_history,
                outputs=[experiment_dropdown, analysis_plots]
            )
            
            # Admin handlers
            async def load_admin_data():
                if not self.current_user or self.current_user.role != UserRole.ADMIN:
                    return None, None
                
                metrics = await self.db_manager.get_system_metrics()
                users = await self.db_manager.get_all_users()
                
                user_df = pd.DataFrame(users)
                return metrics, user_df
            
            if admin_tab:
                admin_tab.select(
                    load_admin_data,
                    outputs=[system_metrics, user_stats]
                )
        
        return app 