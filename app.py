from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import os
from datetime import datetime

app = Flask(__name__)

def generate_car_numbers(specific_digits=None, position_digits=None, modulo_x=None):
    """
    Generate 4-digit car numbers based on custom rules
    
    Args:
        specific_digits: Dict with digit as key and count as value
        position_digits: Dict with position (1-4) as key and digit as value
        modulo_x: X value where sum % 9 == X
    """
    valid_numbers = []
    
    for num in range(10000):  # 0000 to 9999
        # Convert to 4-digit string
        num_str = f"{num:04d}"
        digits = [int(d) for d in num_str]
        
        # Check specific digits
        if specific_digits:
            valid = True
            for digit, required_count in specific_digits.items():
                if num_str.count(str(digit)) != required_count:
                    valid = False
                    break
            if not valid:
                continue
        
        # Check position-specific digits
        if position_digits:
            valid = True
            for position, required_digit in position_digits.items():
                # Position is 1-indexed, convert to 0-indexed
                if digits[position - 1] != required_digit:
                    valid = False
                    break
            if not valid:
                continue
        
        # Check sum condition (simplified - only modulo)
        if modulo_x is not None:
            digit_sum = sum(digits)
            if digit_sum % 9 != modulo_x:
                continue
        
        valid_numbers.append(num_str)
    
    return valid_numbers

def create_pdf(numbers, criteria):
    """Create PDF with the generated numbers"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=1,
        textColor=colors.grey
    )
    
    # Add title
    title = Paragraph("4-Digit Car Number Generator Results", title_style)
    elements.append(title)
    
    # Add generation info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subtitle = Paragraph(f"Generated on: {timestamp}<br/>Total Numbers Found: {len(numbers)}", subtitle_style)
    elements.append(subtitle)
    
    # Add criteria used
    if criteria:
        criteria_text = "<b>Criteria Applied:</b><br/>"
        for criterion in criteria:
            criteria_text += f"• {criterion}<br/>"
        criteria_para = Paragraph(criteria_text, styles['Normal'])
        elements.append(criteria_para)
        elements.append(Spacer(1, 20))
    
    if numbers:
        # Create table with numbers (8 columns for better fit)
        cols = 8
        rows = []
        for i in range(0, len(numbers), cols):
            row = numbers[i:i+cols]
            # Pad row if necessary
            while len(row) < cols:
                row.append("")
            rows.append(row)
        
        table = Table(rows, colWidths=[72]*cols)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        elements.append(table)
    else:
        no_results = Paragraph("No numbers match the specified criteria.", styles['Normal'])
        elements.append(no_results)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        
        # Parse input data (removed zero_count as it's handled in specific_digits)
        
        # Parse specific digits
        specific_digits = {}
        if data.get('specific_digits'):
            for item in data['specific_digits']:
                if item['digit'] != '' and item['count'] != '':
                    specific_digits[int(item['digit'])] = int(item['count'])
        
        # Parse position digits
        position_digits = {}
        if data.get('position_digits'):
            for item in data['position_digits']:
                if item['position'] != '' and item['digit'] != '':
                    position_digits[int(item['position'])] = int(item['digit'])
        
        # Parse sum condition - simplified to just desired sum (1-9)
        modulo_x = None
        desired_sum = data.get('desired_sum')
        if desired_sum and desired_sum != '':
            modulo_x = int(desired_sum) % 9
        
        # Generate numbers (removed zero_count parameter)
        numbers = generate_car_numbers(
            specific_digits=specific_digits if specific_digits else None,
            position_digits=position_digits if position_digits else None,
            modulo_x=modulo_x
        )
        
        # Create criteria list for PDF (removed zero_count, simplified sum)
        criteria = []
        if specific_digits:
            for digit, count in specific_digits.items():
                criteria.append(f"Digit {digit} appears {count} time(s)")
        if position_digits:
            for pos, digit in position_digits.items():
                criteria.append(f"Position {pos} has digit {digit}")
        if modulo_x is not None:
            criteria.append(f"Sum of digits % 9 = {modulo_x} (includes sums: {', '.join([str(i) for i in range(modulo_x, 37, 9) if i <= 36])})")
        
        # Create PDF
        pdf_buffer = create_pdf(numbers, criteria)
        
        # Save PDF temporarily
        pdf_filename = f"car_numbers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join('temp', pdf_filename)
        
        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        return jsonify({
            'success': True,
            'count': len(numbers),
            'preview': numbers[:20],  # First 20 numbers for preview
            'pdf_url': f'/download/{pdf_filename}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_pdf(filename):
    try:
        file_path = os.path.join('temp', filename)
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 404

if __name__ == '__main__':
    # Create temp directory
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True, port=5000)