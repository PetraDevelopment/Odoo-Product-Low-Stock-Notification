from dataclasses import field
from email.policy import default
from odoo import models, fields, api,tools,_
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from odoo.exceptions import UserError
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from email.mime.application import MIMEApplication
from reportlab.platypus import Frame
import re
from io import BytesIO
from reportlab.platypus import Image
from reportlab.platypus import Image as PlatypusImage
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os
from bs4 import BeautifulSoup
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from odoo.modules import get_resource_path
from odoo.exceptions import UserError
import os
from ..external_packages.arabic_reshaper import arabic_reshaper
from ..external_packages.bidi import algorithm
from odoo import fields
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import base64

class StockNotification(models.TransientModel):
    _inherit = "res.config.settings"

    Notification_Based_On = fields.Selection([
        ('option1', 'On hand quantity'),
        ('option2', 'Forcast'),
    ],string=' ',default='option1', required=True)
    Min_Quantity_Based_On = fields.Selection([
        ('option1', 'Global for all product'),
        ('option2', 'individual for all products'),
        ('option3', 'Reorder Rules'),
    ],string=' ',default="option1", required=True)
    Quantity_Limit=fields.Float(string=" " , default='10.0')
    Apply_On = fields.Selection([
        ('option1', 'Product'),
        ('option2', 'Product Variant'),
    ],string=' ', default='option1',required=True)
    @api.model
    def get_values(self):
        res = super(StockNotification, self).get_values()
        config = self.env['ir.config_parameter'].sudo()
        res.update(
            Notification_Based_On=config.get_param('Notification_Based_On', default='option1'),
            Min_Quantity_Based_On=config.get_param('Min_Quantity_Based_On', default='option1'),
            Quantity_Limit=float(config.get_param('Quantity_Limit', default=10.0)),
            Apply_On=config.get_param('Apply_On', default='option1'),
        )
        return res

    def set_values(self):
        super(StockNotification, self).set_values()
        config = self.env['ir.config_parameter'].sudo()
        config.set_param('Notification_Based_On', self.Notification_Based_On)
        config.set_param('Min_Quantity_Based_On', self.Min_Quantity_Based_On)
        config.set_param('Quantity_Limit', str(self.Quantity_Limit))
        config.set_param('Apply_On', self.Apply_On)

    def generate_pdf_attachment(self):
        # Create a BytesIO buffer to store the PDF content in memory
        buffer = BytesIO()
        
        # Create a PDF document using ReportLab's SimpleDocTemplate, with letter-sized pages
        pdf_document = SimpleDocTemplate(buffer, pagesize=letter)
        pdf_content = []
        company = self.env.company
        # Add company logo
        company_logo = company.logo
        if company_logo:
            try:
                image_data = base64.b64decode(company_logo)
                # Check if image_data is not empty
                if image_data:
                    logo = Image(BytesIO(image_data), width=70, height=70, hAlign='LEFT')  # Adjust width and height as needed
                    pdf_content.append(logo)
                else:
                    print("Image data is empty.")
            except Exception as e:
                print(f"Error decoding base64 image data: {e}")

        # Get company details
        
        company_name = company.name if company.name else ''
        company_address = company.street if company.street else ''
        company_city = company.city if company.city else ''
        company_country = company.country_id.name if company.country_id else ''
        company_phone = company.phone if company.phone else ''

        # Construct company details paragraph
        company_details = "<br/>".join(filter(None, [
            company_name,
            company_address,
            company_city,
            company_country,
            company_phone
        ]))
        company_details_style = ParagraphStyle(
            'CompanyDetails',
            parent=getSampleStyleSheet()['BodyText'],
            leftIndent=0,  # Indent company details to the right
        )
        company_details_paragraph = Paragraph(company_details, company_details_style)
        pdf_content.append(company_details_paragraph)




        # Add a header to the PDF
        heading_text = "Product Low Stock Report"
        heading_style = ParagraphStyle(
            'Heading1',
            parent=getSampleStyleSheet()['Heading1'],
            alignment=1,  # 0=left, 1=center, 2=right
        )
        heading_paragraph = Paragraph(heading_text, heading_style)
        pdf_content.append(heading_paragraph)

        # Add a line break after the header
        pdf_content.append(Spacer(1, 12))        

        settings = self.env['res.config.settings'].sudo().get_values()
        quantity_limit = settings['Quantity_Limit']
        Notification = settings['Notification_Based_On']
        Min =settings['Min_Quantity_Based_On']
        Apply=settings['Apply_On']
        min_qty = self.env['ir.config_parameter'].sudo().get_param('product.template.Min_Qty', default='10')
        table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
        current_company = self.env.company

        if current_company.lowStock :
            
            if (Notification == 'option1' and Min == 'option1' and Apply == 'option1'):
                products = self.env['product.template'].search([('qty_available', '<', quantity_limit)])
                # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                
                # Iterate through values in the data dictionary and populate the table
                for product in products:
                    quantity_available = product.qty_available
                    quantity_needed = max(0, quantity_limit - quantity_available)
                    table_data.append([
                        product.name,  # Use product.name directly, assuming it's a string
                        str(quantity_limit),          # Assuming '10' is a placeholder for minimum quantity
                        str(quantity_available),  # Convert quantity_available to string
                        str(quantity_needed)      # Convert quantity_needed to string
                    ])
            elif (Notification == 'option2' and Min == 'option1' and Apply == 'option1'):
                products = self.env['product.template'].search([('virtual_available', '<', quantity_limit)])
                # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                
                # Iterate through values in the data dictionary and populate the table
                for product in products:
                    quantity_available = product.virtual_available
                    quantity_needed = max(0, quantity_limit - quantity_available)
                    table_data.append([
                        product.name,  # Use product.name directly, assuming it's a string
                        str(quantity_limit),          # Assuming '10' is a placeholder for minimum quantity
                        str(quantity_available),  # Convert quantity_available to string
                        str(quantity_needed)      # Convert quantity_needed to string
                    ])
            
            elif (Notification == 'option1' and Min == 'option1' and Apply == 'option2'):
                products = self.env['product.product'].search([('virtual_available', '<', quantity_limit)])
                # Add a table to display data
                table_data = [['Product Name','Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                
                # Iterate through values in the data dictionary and populate the table
                for product in products:
                    quantity_available = product.virtual_available
                    quantity_needed = max(0, quantity_limit - quantity_available)
                    variant_values = ' , '.join([
                        f"{attr_value.attribute_id.name} : {attr_value.name}"
                        for attr_value in product.product_template_variant_value_ids
                    ])
                    product_and_variant = f"{product.name}  {variant_values}"
                    table_data.append([
                        product_and_variant,
                        #  - {variant_info}",  # Use product.name directly, assuming it's a string
                        str(quantity_limit),          # Assuming '10' is a placeholder for minimum quantity
                        str(quantity_available),  # Convert quantity_available to string
                        str(quantity_needed)      # Convert quantity_needed to string
                    ])

            elif (Notification == 'option2' and Min == 'option1' and Apply == 'option2'):
                products = self.env['product.product'].search([('qty_available', '<', quantity_limit)])
                # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                
                # Iterate through values in the data dictionary and populate the table
                for product in products:
                    quantity_available = product.qty_available
                    quantity_needed = max(0, quantity_limit - quantity_available)
                    variant_values = ' , '.join([
                        f"{attr_value.attribute_id.name} : {attr_value.name}"
                        for attr_value in product.product_template_variant_value_ids
                    ])
                    product_and_variant = f"{product.name}  {variant_values}"
                    table_data.append([
                        product_and_variant,  # Use product.name directly, assuming it's a string
                        str(quantity_limit),          # Assuming '10' is a placeholder for minimum quantity
                        str(quantity_available),  # Convert quantity_available to string
                        str(quantity_needed)      # Convert quantity_needed to string
                    ])

            elif (Notification == 'option1' and Min == 'option2' and Apply == 'option1'):
                
                # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                
                products = self.env['product.template'].search([])
                for product in products:
                     # Get Min_Qty from the product record
                    min_qty = product.Min_Qty or 0  # Use 0 if Min_Qty is not set
                    
                    # Filter products where qty_available is less than Min_Qty
                    if product.qty_available < min_qty:
                        quantity_available = product.qty_available
                        quantity_needed = max(0, min_qty - quantity_available)
                        table_data.append([
                            product.name,
                            str(min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ])
            elif (Notification == 'option2' and Min == 'option2' and Apply == 'option1'):
                
                    # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                    
                products = self.env['product.template'].search([])
                for product in products:
                    # Get Min_Qty from the product record
                    min_qty = product.Min_Qty or 0  # Use 0 if Min_Qty is not set
                    
                    # Filter products where qty_available is less than Min_Qty
                    if product.virtual_available < min_qty:
                        quantity_available = product.virtual_available
                        quantity_needed = max(0, min_qty - quantity_available)
                        table_data.append([
                            product.name,
                            str(min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ])   
            elif (Notification == 'option2' and Min == 'option2' and Apply == 'option2'):
                
                    # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                    
                products = self.env['product.product'].search([])
                
                for product in products:
                    # Get Min_Qty from the product record
                    min_qty = product.Min_Qty or 0  # Use 0 if Min_Qty is not set
                    variant_values = ' , '.join([
                        f"{attr_value.attribute_id.name} : {attr_value.name}"
                        for attr_value in product.product_template_variant_value_ids
                    ])
                    product_and_variant = f"{product.name}  {variant_values}"
                    # Filter products where qty_available is less than Min_Qty
                    if product.virtual_available < min_qty:
                        quantity_available = product.virtual_available
                        quantity_needed = max(0, min_qty - quantity_available)
                        table_data.append([
                            product_and_variant,
                            str(min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ]) 
            elif (Notification == 'option1' and Min == 'option2' and Apply == 'option2'):
                
                # Add a table to display data
                table_data = [['Product Name', 'Minimum Quantity', 'Product Quantity', 'Required Quantity']]
                    
                products = self.env['product.product'].search([])
                for product in products:
                    # Get Min_Qty from the product record
                    min_qty = product.Min_Qty or 0  # Use 0 if Min_Qty is not set
                    variant_values = ' , '.join([
                        f"{attr_value.attribute_id.name} : {attr_value.name}"
                        for attr_value in product.product_template_variant_value_ids
                    ])
                    product_and_variant = f"{product.name}  {variant_values}"
                    # Filter products where qty_available is less than Min_Qty
                    if product.qty_available < min_qty:
                        quantity_available = product.qty_available
                        quantity_needed = max(0, min_qty - quantity_available)
                        table_data.append([
                            product_and_variant,
                            str(min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ])                     

            elif (Notification == 'option1' and Min == 'option3' and (Apply == 'option1' or Apply == 'option2') ):
    
                products = self.env['stock.warehouse.orderpoint'].search([])
                
                for product in products:
                    # Filter products where qty_available is less than Min_Qty
                    if product.qty_on_hand < product.product_min_qty:
                        quantity_available = product.qty_on_hand
                        quantity_needed = max(0, product.product_min_qty - quantity_available)
                        table_data.append([
                            product.product_id.name,
                            str(product.product_min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ])    

            elif (Notification == 'option2' and Min == 'option3' and  (Apply == 'option1' or Apply == 'option2') ):
                    
                products = self.env['stock.warehouse.orderpoint'].search([])
                
                for product in products:
                    # Filter products where qty_available is less than Min_Qty
                    if product.qty_forecast < product.product_min_qty:
                        quantity_available = product.qty_forecast
                        quantity_needed = max(0, product.product_min_qty - quantity_available)
                        table_data.append([
                            product.product_id.name,
                            str(product.product_min_qty),
                            str(quantity_available),
                            str(quantity_needed)
                        ])                                               
        else:
            print("Low Stock Notification is disabled for this company or User")
        
        font_file_path = get_resource_path('Product_Low_Stock_Notification', 'static/src/fonts', 'trado.ttf')

        
        try:
            with open(font_file_path, "rb") as file:
                # Read the entire contents of the file
                font_contents = file.read()
                print("Font file contents:", font_contents)
                pdfmetrics.registerFont(TTFont('ArabicFont', font_file_path))
        except FileNotFoundError:
            print("Font file not found.")
        except IOError as e:
            print("Error reading font file:", e)
        # Define styles for the table
        table_style = [
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),  # Set background color for the entire table
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('FONTNAME', (0, 0), (-1, -1), 'ArabicFont'),
        ]
        pdf_table = Table(table_data)
        def is_arabic(text):
            # Arabic characters range in Unicode
            arabic_range = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
            return bool(arabic_range.search(text))

        # Iterate through the table cells and reshape text if necessary
        for i in range(len(pdf_table._cellvalues)):
            for j in range(len(pdf_table._cellvalues[i])):
                if isinstance(pdf_table._cellvalues[i][j], str) and pdf_table._cellvalues[i][j].strip():
                    text = pdf_table._cellvalues[i][j]
                    # Check if the text contains Arabic characters
                    if is_arabic(text):
                        # Reshape Arabic text
                        reshaped_text = arabic_reshaper.reshape(text)
                        # Add RTL markers
                        rtl_text = algorithm.get_display(reshaped_text)
                        pdf_table._cellvalues[i][j] = rtl_text

        pdf_table.setStyle(TableStyle(table_style))

        # Add the table to the content
        pdf_content.append(pdf_table)
            # Build the PDF document
        pdf_document.build(pdf_content)

        # Move the buffer position to the beginning
        buffer.seek(0)

        # Return the buffer containing the generated PDF content
        return buffer.getvalue()


    @classmethod
    def is_valid_email(cls, email):
        # Check if the email is not provided (empty or None)
        if not email:
            # If email is not provided, return False
            return False
        
        # Define a regular expression pattern for a valid email address
        email_regex = r'^\S+@\S+\.\S+$'
        
        # Use the re.match function to check if the email matches the defined pattern
        # The result is not None if there is a match, indicating a valid email
        return re.match(email_regex, email) is not None   

    @api.model    
    def action_low_stock_send(self):
        # Generate the PDF attachment
        pdf_buffer = self.generate_pdf_attachment()

        current_company = self.env.company
        users = self.env['res.users'].search([('company_id', '=', current_company.id)])
        if not current_company.lowStock:
            return

        # Get all user emails
        users = self.env['res.users'].search([('company_id', '=', current_company.id)])
        
        # Access the ir.mail_server model
        mail_server_model = self.env['ir.mail_server']

        # Retrieve the SMTP server record
        mail_server = mail_server_model.search([], limit=1)

        # Create the email message for each user
        smtp_server = mail_server.smtp_host
        smtp_port = mail_server.smtp_port
        smtp_username = mail_server.smtp_user
        smtp_password = mail_server.smtp_pass
        
        for user in users:
            if self.is_valid_email(user.login) and self.is_valid_email(smtp_username) and user.Notify:
                msg = MIMEMultipart()
                msg['From'] = smtp_username
                msg['To'] = user.login  # User's email address
                msg['Subject'] = 'PDF Report'

                # Attach PDF
                pdf_attachment = MIMEApplication(pdf_buffer, _subtype="pdf")
                pdf_attachment.add_header('content-disposition', 'attachment', filename='report.pdf')
                msg.attach(pdf_attachment)

                # Connect to SMTP server and send email
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(smtp_username, user.login, msg.as_string())
            else: 
                continue
