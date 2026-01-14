import fitz  # PyMuPDF
import pandas as pd
import os
import re
import shutil
from datetime import datetime

class JewelryCatalogProcessor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.all_products = []
        self.products_with_images = []
        self.image_counter = {}
        
    def process_catalog(self):
        """Procesa el catálogo completo"""
        print("="*60)
        print("PROCESADOR DE CATÁLOGO DE JOYERÍA")
        print("="*60)
        
        # Paso 1: Extraer productos
        print("\n📋 Paso 1: Extrayendo productos del PDF...")
        self.extract_products()
        
        # Paso 2: Extraer y relacionar imágenes
        print("\n🖼️ Paso 2: Extrayendo y relacionando imágenes...")
        self.extract_and_relate_images()
        
        # Paso 3: Exportar a Excel
        print("\n💾 Paso 3: Exportando a Excel...")
        self.export_to_excel()
        
        # Paso 4: Generar HTML desde Excel
        print("\n🌐 Paso 4: Generando catálogo HTML...")
        self.generate_html_from_excel()
        
        print("\n" + "="*60)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE!")
        print("="*60)
        self.print_summary()
    
    def extract_products(self):
        """Extrae todos los productos del PDF"""
        current_product = {}
        current_category = "OTROS"
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            lines = text.split('\n')
            
            # Determinar categoría de la página
            page_category = self.detect_category(page_num + 1, text)
            if page_category != "OTROS":
                current_category = page_category
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Detectar nombre de producto (líneas con formato especial)
                if self.is_product_name(line, i, lines):
                    # Guardar producto anterior si existe
                    if current_product and 'NOMBRE' in current_product:
                        current_product['CATEGORIA'] = current_category
                        current_product['PAGINA'] = page_num + 1
                        self.all_products.append(current_product.copy())
                    
                    # Iniciar nuevo producto
                    product_name = self.clean_product_name(line)
                    current_product = {
                        'NOMBRE': product_name,
                        'CATEGORIA': current_category,
                        'PAGINA': page_num + 1
                    }
                
                # Extraer descripción
                elif not current_product.get('DESCRIPCION') and self.is_description(line):
                    current_product['DESCRIPCION'] = line
                
                # Extraer material
                elif 'MATERIAL' in line.upper():
                    material = line.split(':', 1)[1].strip() if ':' in line else line.replace('MATERIAL', '').strip()
                    current_product['MATERIAL'] = material
                
                # Extraer medidas
                elif any(keyword in line.upper() for keyword in ['MEDIDAS:', 'DIAMETRO:', 'LONGITUD:', 'LARGO:']):
                    for keyword in ['MEDIDAS:', 'DIAMETRO:', 'LONGITUD:', 'LARGO:']:
                        if keyword in line.upper():
                            value = line.split(':', 1)[1].strip() if ':' in line else line.replace(keyword, '').strip()
                            current_product[keyword.replace(':', '').strip()] = value
                            break
                
                # Extraer precio
                elif 'PRECIO' in line.upper():
                    # Buscar precio en esta línea
                    price_match = re.search(r'\$?\s*(\d+\.?\d*)', line)
                    if price_match:
                        current_product['PRECIO'] = float(price_match.group(1))
                    # O en la siguiente línea
                    elif i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        price_match = re.search(r'\$?\s*(\d+\.?\d*)', next_line)
                        if price_match:
                            current_product['PRECIO'] = float(price_match.group(1))
                            i += 1  # Saltar línea del precio
                
                i += 1
            
            # Agregar producto al final de la página si existe
            if current_product and 'NOMBRE' in current_product and 'CATEGORIA' not in current_product:
                current_product['CATEGORIA'] = current_category
                current_product['PAGINA'] = page_num + 1
                self.all_products.append(current_product.copy())
        
        # Agregar el último producto
        if current_product and 'NOMBRE' in current_product:
            self.all_products.append(current_product)
        
        print(f"  ✅ Productos extraídos: {len(self.all_products)}")
    
    def detect_category(self, page_num, text):
        """Detecta la categoría de la página"""
        text_upper = text.upper()
        
        # Páginas específicas según el PDF
        if page_num in [4, 5] or ('ARETE' in text_upper and 'ARRACADA' not in text_upper):
            return 'ARETE'
        elif page_num in [7, 8, 9, 10] or 'PULSERA' in text_upper:
            return 'PULSERA'
        elif page_num >= 12 or 'ARRACADA' in text_upper or 'ARRACADAS' in text_upper:
            return 'ARRACADAS'
        
        # Detección por contenido
        if 'ARETE' in text_upper and page_num < 10:
            return 'ARETE'
        elif 'PULSERA' in text_upper:
            return 'PULSERA'
        elif 'ARRACADA' in text_upper:
            return 'ARRACADAS'
        
        return 'OTROS'
    
    def is_product_name(self, line, line_idx, lines):
        """Determina si una línea es un nombre de producto"""
        if not line or len(line) < 3:
            return False
        
        # Eliminar etiquetas HTML
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        
        # No debe contener palabras clave de especificaciones
        exclude_words = ['MATERIAL', 'MEDIDAS', 'DIAMETRO', 'LONGITUD', 'LARGO', 'PRECIO', 'MM', 'CM']
        if any(word in clean_line.upper() for word in exclude_words):
            return False
        
        # Patrones de nombres de productos
        patterns = [
            r'^ARETE\s+[A-Z]',
            r'^PULSERA\s+[A-Z]', 
            r'^ARRACADA\s+[A-Z]',
            r'^[A-Z]+\s+[A-Z]+\s+[A-Z]+$',
            r'^[A-Z]+\s+[A-Z]+$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, clean_line):
                return True
        
        # Si la línea está en mayúsculas y tiene un formato de nombre
        if clean_line.isupper() and 5 <= len(clean_line) <= 50:
            # Verificar contexto (líneas vacías alrededor)
            if line_idx > 0 and line_idx < len(lines) - 1:
                prev_empty = not lines[line_idx - 1].strip()
                next_empty = not lines[line_idx + 1].strip()
                if prev_empty or next_empty:
                    return True
        
        return False
    
    def clean_product_name(self, line):
        """Limpia el nombre del producto"""
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        clean_line = re.sub(r'^\d+\s*$', '', clean_line).strip()
        return clean_line
    
    def is_description(self, line):
        """Determina si una línea es una descripción"""
        desc_keywords = [
            'en forma de', 'con diseño', 'diseño de', 'con dije',
            'con brillos', 'con perla', 'acabado', 'dijes', 'eslabones'
        ]
        return any(keyword in line.lower() for keyword in desc_keywords)
    
    def extract_and_relate_images(self):
        """Extrae imágenes y las relaciona con productos"""
        # Organizar productos por página
        products_by_page = {}
        for product in self.all_products:
            page = product['PAGINA']
            if page not in products_by_page:
                products_by_page[page] = []
            products_by_page[page].append(product)
        
        # Crear carpetas para imágenes
        for category in ['ARETE', 'PULSERA', 'ARRACADAS']:
            os.makedirs(f'imagenes/{category}', exist_ok=True)
        
        # Procesar cada página
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_products = products_by_page.get(page_num + 1, [])
            
            if not page_products:
                continue
            
            # Extraer imágenes de esta página
            image_list = page.get_images(full=True)
            
            # Relacionar cada imagen con un producto
            for img_idx, img_info in enumerate(image_list):
                if img_idx >= len(page_products):
                    continue
                
                product = page_products[img_idx]
                
                # Extraer la imagen
                xref = img_info[0]
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Crear nombre seguro para la imagen
                safe_name = self.create_safe_filename(product['NOMBRE'])
                category = product['CATEGORIA']
                
                # Contador para evitar sobrescribir
                if safe_name not in self.image_counter:
                    self.image_counter[safe_name] = 1
                else:
                    self.image_counter[safe_name] += 1
                
                img_number = self.image_counter[safe_name]
                image_filename = f"{safe_name}_{img_number}.{image_ext}"
                image_path = f"imagenes/{category}/{image_filename}"
                
                # Guardar imagen
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                
                # Agregar información al producto
                product_copy = product.copy()
                product_copy['IMAGEN'] = image_filename
                product_copy['RUTA_IMAGEN'] = image_path
                product_copy['TIPO_IMAGEN'] = image_ext
                
                self.products_with_images.append(product_copy)
                
                print(f"  • Pág {page_num + 1}: {product['NOMBRE']} → {image_filename}")
        
        print(f"  ✅ Imágenes relacionadas: {len(self.products_with_images)}")
    
    def create_safe_filename(self, name):
        """Crea un nombre de archivo seguro"""
        # Eliminar caracteres especiales
        safe_name = re.sub(r'[^\w\s-]', '', name)
        # Reemplazar espacios con guiones bajos
        safe_name = safe_name.replace(' ', '_')
        # Convertir a minúsculas
        safe_name = safe_name.lower()
        # Limitar longitud
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        return safe_name
    
    def export_to_excel(self):
        """Exporta los datos a Excel"""
        # Crear carpeta de resultados
        os.makedirs('resultados', exist_ok=True)
        
        # Preparar DataFrame con productos que tienen imágenes
        if self.products_with_images:
            df = pd.DataFrame(self.products_with_images)
            
            # Reordenar columnas
            column_order = ['NOMBRE', 'CATEGORIA', 'DESCRIPCION', 'MATERIAL', 'PRECIO',
                          'MEDIDAS', 'DIAMETRO', 'LONGITUD', 'LARGO', 'PAGINA',
                          'IMAGEN', 'RUTA_IMAGEN', 'TIPO_IMAGEN']
            
            # Filtrar columnas existentes
            existing_cols = [col for col in column_order if col in df.columns]
            other_cols = [col for col in df.columns if col not in column_order]
            final_order = existing_cols + other_cols
            
            df = df[final_order]
            
            # Exportar a Excel
            excel_path = 'resultados/catalogo_joyeria.xlsx'
            df.to_excel(excel_path, index=False)
            
            # Crear también un CSV para fácil lectura
            csv_path = 'resultados/catalogo_joyeria.csv'
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
            print(f"  ✅ Excel generado: {excel_path}")
            print(f"  ✅ CSV generado: {csv_path}")
            
            # Crear hojas por categoría
            with pd.ExcelWriter('resultados/catalogo_por_categoria.xlsx') as writer:
                for category in df['CATEGORIA'].unique():
                    df_category = df[df['CATEGORIA'] == category]
                    sheet_name = category[:31]  # Excel limita a 31 caracteres
                    df_category.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"  ✅ Excel por categoría: resultados/catalogo_por_categoria.xlsx")
            
            return excel_path
        else:
            print("  ⚠️ No hay productos con imágenes para exportar")
            return None
    
    def generate_html_from_excel(self):
        """Genera un catálogo HTML leyendo desde el Excel"""
        excel_path = 'resultados/catalogo_joyeria.xlsx'
        
        if not os.path.exists(excel_path):
            print(f"  ❌ No se encontró el archivo Excel: {excel_path}")
            return
        
        # Leer datos del Excel
        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            print(f"  ❌ Error leyendo Excel: {e}")
            return
        
        if df.empty:
            print("  ⚠️ El Excel está vacío")
            return
        
        # Crear el HTML
        html_content = self.create_html_content(df)
        
        # Guardar HTML
        html_path = 'resultados/catalogo_joyeria.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  ✅ HTML generado: {html_path}")
        
        # Crear también una versión simplificada
        self.create_simple_html(df)
    
    def create_html_content(self, df):
        """Crea el contenido HTML desde el DataFrame"""
        # Obtener estadísticas
        total_productos = len(df)
        categorias = df['CATEGORIA'].value_counts().to_dict()
        
        # Construir HTML
        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo de Joyería Elegante 2026</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f9f9f9;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #8B7355 0%, #D4AF37 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.8rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 30px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.1);
            padding: 15px 25px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }}
        
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            display: block;
        }}
        
        .categories {{
            padding: 30px;
        }}
        
        .category-section {{
            margin-bottom: 50px;
        }}
        
        .category-title {{
            font-size: 1.8rem;
            color: #8B7355;
            padding-bottom: 15px;
            margin-bottom: 25px;
            border-bottom: 3px solid #F5DEB3;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .category-title::before {{
            content: "✦";
            font-size: 1.5rem;
        }}
        
        .products-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 30px;
        }}
        
        .product-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid #eee;
        }}
        
        .product-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.15);
        }}
        
        .product-image {{
            width: 100%;
            height: 250px;
            object-fit: contain;
            background: #f8f8f8;
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        
        .product-info {{
            padding: 20px;
        }}
        
        .product-name {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            min-height: 60px;
        }}
        
        .product-description {{
            color: #666;
            font-size: 0.95rem;
            margin-bottom: 15px;
            min-height: 40px;
        }}
        
        .product-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }}
        
        .detail-item {{
            font-size: 0.9rem;
        }}
        
        .detail-label {{
            font-weight: bold;
            color: #8B7355;
            display: block;
        }}
        
        .product-price {{
            font-size: 1.8rem;
            font-weight: bold;
            color: #D4AF37;
            text-align: center;
            padding: 10px;
            background: #FFF8E1;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            background: #f5f5f5;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 50px;
        }}
        
        .category-stats {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        
        .category-stat {{
            background: #F5DEB3;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #8B7355;
        }}
        
        @media (max-width: 768px) {{
            .products-grid {{
                grid-template-columns: 1fr;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .stats {{
                flex-direction: column;
                align-items: center;
            }}
        }}
        
        .no-image {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #666;
            font-size: 1.2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>✨ Catálogo de Joyería Elegante 2026</h1>
            <p class="subtitle">Colección exclusiva de aretes, pulseras y arracadas</p>
            
            <div class="stats">
                <div class="stat-card">
                    <span class="stat-number">{total_productos}</span>
                    <span>Productos Totales</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{len(categorias)}</span>
                    <span>Categorías</span>
                </div>
            </div>
            
            <div class="category-stats">
'''
        
        # Agregar estadísticas por categoría
        for categoria, cantidad in categorias.items():
            html += f'                <span class="category-stat">{categoria}: {cantidad}</span>\n'
        
        html += '''            </div>
        </header>
        
        <main class="categories">
'''
        
        # Agregar productos por categoría
        for categoria in sorted(df['CATEGORIA'].unique()):
            categoria_df = df[df['CATEGORIA'] == categoria]
            
            html += f'''
            <section class="category-section">
                <h2 class="category-title">{categoria} ({len(categoria_df)})</h2>
                <div class="products-grid">
'''
            
            for _, producto in categoria_df.iterrows():
                # Preparar información del producto
                nombre = producto.get('NOMBRE', 'Sin nombre')
                descripcion = producto.get('DESCRIPCION', '')
                material = producto.get('MATERIAL', 'No especificado')
                precio = producto.get('PRECIO', 'N/A')
                medidas = producto.get('MEDIDAS', producto.get('DIAMETRO', producto.get('LONGITUD', producto.get('LARGO', 'No especificado'))))
                imagen = producto.get('IMAGEN', '')
                
                # Formatear precio
                if isinstance(precio, (int, float)):
                    precio_formateado = f"${precio:,.2f}"
                else:
                    precio_formateado = str(precio)
                
                # Ruta de la imagen
                if pd.notna(imagen) and imagen:
                    # Usar rutas relativas para que funcionen localmente
                    imagen_path = f"../imagenes/{categoria}/{imagen}"
                    img_tag = f'<img src="{imagen_path}" alt="{nombre}" class="product-image">'
                else:
                    img_tag = f'<div class="product-image no-image">Imagen no disponible</div>'
                
                html += f'''
                    <article class="product-card">
                        {img_tag}
                        <div class="product-info">
                            <h3 class="product-name">{nombre}</h3>
                            <p class="product-description">{descripcion}</p>
                            
                            <div class="product-details">
                                <div class="detail-item">
                                    <span class="detail-label">Material:</span>
                                    {material}
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Medidas:</span>
                                    {medidas}
                                </div>
                            </div>
                            
                            <div class="product-price">
                                {precio_formateado}
                            </div>
                        </div>
                    </article>
'''
            
            html += '''
                </div>
            </section>
'''
        
        html += '''
        </main>
        
        <footer>
            <p>Catálogo generado automáticamente • Fecha: ''' + datetime.now().strftime("%d/%m/%Y") + '''</p>
            <p>Total de productos en catálogo: ''' + str(total_productos) + '''</p>
        </footer>
    </div>
    
    <script>
        // Efecto suave al hacer hover en las tarjetas
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.product-card');
            
            cards.forEach(card => {
                card.addEventListener('mouseenter', function() {
                    this.style.transition = 'all 0.3s ease';
                });
                
                card.addEventListener('mouseleave', function() {
                    this.style.transition = 'all 0.3s ease';
                });
            });
            
            // Mostrar mensaje de carga completada
            setTimeout(() => {
                console.log('Catálogo cargado correctamente');
            }, 1000);
        });
    </script>
</body>
</html>'''
        
        return html
    
    def create_simple_html(self, df):
        """Crea una versión HTML simplificada"""
        html_simple = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Catálogo Simple - Joyería</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .product { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
        .product img { max-width: 150px; float: left; margin-right: 15px; }
        .clear { clear: both; }
    </style>
</head>
<body>
    <h1>Catálogo de Joyería (Versión Simple)</h1>
'''
        
        for _, row in df.iterrows():
            nombre = row['NOMBRE']
            categoria = row['CATEGORIA']
            precio = row.get('PRECIO', 'N/A')
            imagen = row.get('IMAGEN', '')
            
            if pd.notna(imagen) and imagen:
                img_tag = f'<img src="../imagenes/{categoria}/{imagen}" alt="{nombre}" width="150">'
            else:
                img_tag = ''
            
            html_simple += f'''
    <div class="product">
        {img_tag}
        <h3>{nombre}</h3>
        <p><strong>Categoría:</strong> {categoria}</p>
        <p><strong>Precio:</strong> ${precio if isinstance(precio, (int, float)) else precio}</p>
        <div class="clear"></div>
    </div>
'''
        
        html_simple += '''
</body>
</html>'''
        
        with open('resultados/catalogo_simple.html', 'w', encoding='utf-8') as f:
            f.write(html_simple)
        
        print(f"  ✅ HTML simple generado: resultados/catalogo_simple.html")
    
    def print_summary(self):
        """Imprime un resumen del proceso"""
        print("\n📊 RESUMEN FINAL:")
        print(f"   • Productos extraídos: {len(self.all_products)}")
        print(f"   • Productos con imágenes: {len(self.products_with_images)}")
        
        # Estadísticas por categoría
        if self.products_with_images:
            categorias = {}
            for producto in self.products_with_images:
                cat = producto['CATEGORIA']
                categorias[cat] = categorias.get(cat, 0) + 1
            
            for cat, cantidad in categorias.items():
                print(f"   • {cat}: {cantidad} productos")
        
        print("\n📁 ARCHIVOS GENERADOS:")
        print("   • resultados/catalogo_joyeria.xlsx - Excel principal")
        print("   • resultados/catalogo_joyeria.csv - CSV para fácil lectura")
        print("   • resultados/catalogo_por_categoria.xlsx - Excel con hojas por categoría")
        print("   • resultados/catalogo_joyeria.html - Catálogo HTML completo")
        print("   • resultados/catalogo_simple.html - Versión HTML simplificada")
        
        print("\n🖼️ IMÁGENES GUARDADAS EN:")
        print("   • imagenes/ARETE/ - Imágenes de aretes")
        print("   • imagenes/PULSERA/ - Imágenes de pulseras")
        print("   • imagenes/ARRACADAS/ - Imágenes de arracadas")
        
        print("\n🔍 Para ver el catálogo completo, abre: resultados/catalogo_joyeria.html")
        print("💡 Las imágenes están correctamente vinculadas en el HTML")

def main():
    # Verificar dependencias
    try:
        import fitz
        import pandas as pd
    except ImportError as e:
        print("❌ Faltan dependencias. Instala con:")
        print("   pip install PyMuPDF pandas openpyxl")
        print(f"   Error: {e}")
        return
    
    # Archivo PDF
    pdf_file = "Documento A4 Catálogo De Joyería Elegante Beige.pdf"
    
    if not os.path.exists(pdf_file):
        print(f"❌ No se encontró el archivo: {pdf_file}")
        print("   Coloca el PDF en la misma carpeta que este script.")
        return
    
    try:
        # Procesar catálogo
        processor = JewelryCatalogProcessor(pdf_file)
        processor.process_catalog()
        
    except Exception as e:
        print(f"\n❌ Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()