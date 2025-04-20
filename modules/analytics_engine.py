import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.figure import Figure
import os

class AnalyticsEngine:
    def __init__(self):
        """Initialize Analytics Engine"""
        pass
    
    def generate_score_distribution_chart(self, results_df):
        """Generate score distribution chart"""
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1)
        
        # Create score distribution
        ax.bar(results_df['Question'], results_df['Percentage'], color='skyblue')
        ax.axhline(y=60, color='r', linestyle='--', alpha=0.7, label='Pass Mark (60%)')
        ax.set_xlabel('Question')
        ax.set_ylabel('Score (%)')
        ax.set_title('Question-wise Performance')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Save chart to memory
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        
        # Convert to base64 for embedding in HTML
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return image_base64
    
    def generate_keyword_chart(self, results):
        """Generate keyword matching chart"""
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1)
        
        questions = []
        matched_counts = []
        total_counts = []
        
        for question_id, result in results.items():
            if 'matched_keywords' in result and 'keywords' in result:
                questions.append(question_id)
                matched_counts.append(len(result['matched_keywords']))
                total_counts.append(len(result['keywords']))
        
        x = np.arange(len(questions))
        width = 0.35
        
        ax.bar(x - width/2, matched_counts, width, label='Matched Keywords', color='green')
        ax.bar(x + width/2, total_counts, width, label='Total Keywords', color='blue')
        
        ax.set_xlabel('Questions')
        ax.set_ylabel('Number of Keywords')
        ax.set_title('Keyword Matching Analysis')
        ax.set_xticks(x)
        ax.set_xticklabels(questions)
        ax.legend()
        
        # Save chart to memory
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        
        # Convert to base64 for embedding in HTML
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return image_base64
    
    def generate_overall_performance_chart(self, total_score, max_score):
        """Generate overall performance gauge chart"""
        fig = Figure(figsize=(8, 8))
        ax = fig.add_subplot(1, 1, 1, polar=True)
        
        percentage = (total_score / max_score) * 100
        
        # Define the gauge
        theta = np.linspace(0, 180, 100) * np.pi / 180
        r = [1] * 100
        
        # Define the colors based on performance
        if percentage < 40:
            color = 'red'
        elif percentage < 70:
            color = 'orange'
        else:
            color = 'green'
        
        # Plot the gauge
        ax.plot(theta, r, color='lightgray', linewidth=5)
        gauge_theta = np.linspace(0, percentage * 180 / 100, 100) * np.pi / 180
        ax.plot(gauge_theta, [1] * len(gauge_theta), color=color, linewidth=5)
        
        # Customize the chart
        ax.set_rticks([])
        ax.set_xticks([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax.set_ylim(0, 1.2)
        ax.set_title(f'Overall Performance: {percentage:.1f}%', size=15)
        
        # Save chart to memory
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        
        # Convert to base64 for embedding in HTML
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return image_base64
    
    def generate_performance_report(self, results_df, evaluation_results, total_score, max_score):
        """Generate comprehensive performance report with visualizations"""
        
        # Create a dictionary to store all charts
        charts = {}
        
        # Generate score distribution chart
        charts['score_distribution'] = self.generate_score_distribution_chart(results_df)
        
        # Generate keyword chart
        charts['keyword_matching'] = self.generate_keyword_chart(evaluation_results)
        
        # Generate overall performance chart
        charts['overall_performance'] = self.generate_overall_performance_chart(total_score, max_score)
        
        # Calculate performance metrics
        performance_metrics = {
            'total_score': total_score,
            'max_score': max_score,
            'percentage': (total_score / max_score) * 100 if max_score > 0 else 0,
            'highest_scoring_question': results_df.loc[results_df['Percentage'].idxmax(), 'Question'] if not results_df.empty else 'N/A',
            'lowest_scoring_question': results_df.loc[results_df['Percentage'].idxmin(), 'Question'] if not results_df.empty else 'N/A',
            'pass_rate': len(results_df[results_df['Percentage'] >= 60]) / len(results_df) * 100 if not results_df.empty else 0
        }
        
        return charts, performance_metrics
