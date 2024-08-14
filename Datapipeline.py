from flask import Flask, request, render_template, send_file, flash, redirect
import pandas as pd
import numpy as np
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flashing messages

# Define the upload directory
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to clean the data
def clean_data(df):
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Handle missing values
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].mean())
    categorical_columns = df.select_dtypes(include=[object]).columns
    df[categorical_columns] = df[categorical_columns].fillna(df[categorical_columns].mode().iloc[0])
    
    # Remove outliers using IQR
    for col in numeric_columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        df = df[(df[col] >= (Q1 - 1.5 * IQR)) & (df[col] <= (Q3 + 1.5 * IQR))]
    
    # Convert data types if necessary
    if 'Join Date' in df.columns:
        df['Join Date'] = pd.to_datetime(df['Join Date'], errors='coerce')
    
    # Basic string operations and remove unwanted characters
    for col in categorical_columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
        df[col] = df[col].apply(lambda x: re.sub(r'[/\\><,.]', '', x))
    
    # Clean phone numbers if provided
    if 'Phone No' in df.columns:
        df['Phone No'] = df['Phone No'].astype(str).str.replace(r'\D', '', regex=True)
    
    return df

# Route to upload the file
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                df = pd.read_csv(filepath)
                
                # Check for null values before cleaning
                if df.isnull().sum().sum() == 0:
                    flash('No Errors / Empty Values Present in the given Dataset', 'success')
                    os.remove(filepath)
                    return redirect('/')
                
                cleaned_df = clean_data(df)
                
                # Check for null values after cleaning
                if cleaned_df.isnull().sum().sum() == 0:
                    flash('Data cleaned successfully', 'success')
                else:
                    flash('Some values could not be cleaned properly.', 'warning')
                
                cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cleaned_' + filename)
                cleaned_df.to_csv(cleaned_file_path, index=False)
                
                return_value = send_file(cleaned_file_path, as_attachment=True, download_name='cleaned_' + filename)
                
                # Clean up files
                os.remove(filepath)
                os.remove(cleaned_file_path)
                
                return return_value
            except Exception as e:
                flash(f"An error occurred: {str(e)}", 'error')
                return redirect('/')
        else:
            flash("Please upload a valid CSV file.", 'error')
            return redirect('/')
    return render_template('Upload.html')

if __name__ == '__main__':
    app.run(debug=True)