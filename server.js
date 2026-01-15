const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

const app = express();
const PORT = process.env.PORT || 3000;

// Configuración de multer para subir archivos
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    if (file.fieldname === 'imagen') {
      // Para imágenes: crear carpeta según categoría
      const categoria = req.body.categoria || 'otros';
      const uploadPath = path.join(__dirname, 'public', 'imagenes', categoria.toUpperCase());
      
      if (!fs.existsSync(uploadPath)) {
        fs.mkdirSync(uploadPath, { recursive: true });
      }
      
      cb(null, uploadPath);
    } else {
      // Para otros archivos (CSV)
      const uploadPath = path.join(__dirname, 'uploads');
      if (!fs.existsSync(uploadPath)) {
        fs.mkdirSync(uploadPath, { recursive: true });
      }
      cb(null, uploadPath);
    }
  },
  filename: function (req, file, cb) {
    // Nombre único para el archivo
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage: storage,
  fileFilter: function (req, file, cb) {
    // Aceptar solo imágenes y CSV
    if (file.fieldname === 'imagen' && file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else if (file.fieldname === 'csv' && (file.mimetype === 'text/csv' || file.originalname.endsWith('.csv'))) {
      cb(null, true);
    } else {
      cb(new Error('Tipo de archivo no permitido'));
    }
  }
});

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));
app.use('/imagenes', express.static(path.join(__dirname, 'public', 'imagenes')));

// Ruta para la página principal
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'index.html'));
});

// Ruta para la página de administración
app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, 'views', 'admin.html'));
});

// API: Obtener todos los productos
app.get('/api/productos', (req, res) => {
  const productos = [];
  
  fs.createReadStream('public/productos.csv')
    .pipe(csv())
    .on('data', (row) => {
      productos.push(row);
    })
    .on('end', () => {
      res.json(productos);
    })
    .on('error', (err) => {
      console.error('Error leyendo CSV:', err);
      res.status(500).json({ error: 'Error al leer el archivo CSV' });
    });
});

// API: Agregar nuevo producto CON STOCK
app.post('/api/productos', upload.single('imagen'), (req, res) => {
  try {
    const nuevoProducto = {
      NOMBRE: req.body.nombre || '',
      CATEGORIA: req.body.categoria || '',
      DESCRIPCION: req.body.descripcion || '',
      MATERIAL: req.body.material || 'ACERO INOXIDABLE',
      PRECIO: req.body.precio || '0',
      STOCK: req.body.stock || '0',
      MEDIDAS: req.body.medidas || '',
      DIAMETRO: req.body.diametro || '',
      LONGITUD: req.body.longitud || '',
      LARGO: req.body.largo || '',
      PAGINA: req.body.pagina || '',
      IMAGEN: req.file ? req.file.filename : '',
      RUTA_IMAGEN: req.file ? `/imagenes/${req.body.categoria?.toUpperCase() || 'OTROS'}/${req.file.filename}` : '',
      TIPO_IMAGEN: req.file ? req.file.mimetype.split('/')[1] : ''
    };

    console.log('Nuevo producto recibido:', nuevoProducto);

    // Leer CSV existente
    fs.readFile('public/productos.csv', 'utf8', (err, data) => {
      if (err) {
        console.error('Error leyendo CSV:', err);
        return res.status(500).json({ error: 'Error al leer el archivo CSV' });
      }

      // Agregar nueva línea
      const lines = data.trim().split('\n');
      const newLine = Object.values(nuevoProducto).map(value => `"${value}"`).join(',');
      const updatedCSV = data + (data.endsWith('\n') ? '' : '\n') + newLine;

      // Escribir CSV actualizado
      fs.writeFile('public/productos.csv', updatedCSV, (err) => {
        if (err) {
          console.error('Error escribiendo CSV:', err);
          return res.status(500).json({ error: 'Error al guardar el producto' });
        }
        
        console.log('Producto agregado correctamente');
        res.json({ 
          success: true, 
          message: 'Producto agregado correctamente',
          producto: nuevoProducto 
        });
      });
    });
  } catch (error) {
    console.error('Error procesando producto:', error);
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// API: Eliminar producto
app.delete('/api/productos/:id', (req, res) => {
  const productId = parseInt(req.params.id);
  console.log(`Eliminando producto ID: ${productId}`);
  
  fs.readFile('public/productos.csv', 'utf8', (err, data) => {
    if (err) {
      console.error('Error leyendo CSV:', err);
      return res.status(500).json({ error: 'Error al leer el archivo CSV' });
    }

    const lines = data.trim().split('\n');
    if (productId < 0 || productId >= lines.length) {
      return res.status(404).json({ error: 'Producto no encontrado' });
    }
    
    const headers = lines[0];
    
    // Mantener todas las líneas excepto la que corresponde al ID
    const newLines = [headers];
    for (let i = 1; i < lines.length; i++) {
      if (i !== productId) {
        newLines.push(lines[i]);
      }
    }

    const updatedCSV = newLines.join('\n');
    
    fs.writeFile('public/productos.csv', updatedCSV, (err) => {
      if (err) {
        console.error('Error escribiendo CSV:', err);
        return res.status(500).json({ error: 'Error al eliminar el producto' });
      }
      
      console.log('Producto eliminado correctamente');
      res.json({ 
        success: true, 
        message: 'Producto eliminado correctamente' 
      });
    });
  });
});

// API: Actualizar producto COMPLETO
app.put('/api/productos/:id', upload.single('imagen'), (req, res) => {
  const productId = parseInt(req.params.id);
  console.log(`Actualizando producto ID: ${productId}`, req.body);
  
  fs.readFile('public/productos.csv', 'utf8', (err, data) => {
    if (err) {
      console.error('Error leyendo CSV:', err);
      return res.status(500).json({ error: 'Error al leer el archivo CSV' });
    }

    const lines = data.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.replace(/"/g, ''));
    
    if (productId < 0 || productId >= lines.length) {
      return res.status(404).json({ error: 'Producto no encontrado' });
    }

    // Obtener producto actual
    const currentValues = lines[productId].split(',').map(v => v.replace(/"/g, ''));
    const currentProduct = {};
    headers.forEach((header, index) => {
      currentProduct[header] = currentValues[index] || '';
    });

    // Construir objeto actualizado
    const updatedProduct = { ...currentProduct };
    
    // Actualizar campos si vienen en la solicitud
    if (req.body.nombre) updatedProduct.NOMBRE = req.body.nombre;
    if (req.body.categoria) updatedProduct.CATEGORIA = req.body.categoria;
    if (req.body.descripcion !== undefined) updatedProduct.DESCRIPCION = req.body.descripcion;
    if (req.body.material) updatedProduct.MATERIAL = req.body.material;
    if (req.body.precio) updatedProduct.PRECIO = req.body.precio;
    if (req.body.stock !== undefined) updatedProduct.STOCK = req.body.stock;
    if (req.body.medidas !== undefined) updatedProduct.MEDIDAS = req.body.medidas;
    if (req.body.diametro !== undefined) updatedProduct.DIAMETRO = req.body.diametro;
    if (req.body.longitud !== undefined) updatedProduct.LONGITUD = req.body.longitud;
    if (req.body.largo !== undefined) updatedProduct.LARGO = req.body.largo;
    if (req.body.pagina !== undefined) updatedProduct.PAGINA = req.body.pagina;

    // Si hay nueva imagen
    if (req.file) {
      updatedProduct['IMAGEN'] = req.file.filename;
      updatedProduct['RUTA_IMAGEN'] = `/imagenes/${req.body.categoria || updatedProduct.CATEGORIA}/${req.file.filename}`;
      updatedProduct['TIPO_IMAGEN'] = req.file.mimetype.split('/')[1];
    }

    // Actualizar la línea específica
    const updatedLine = headers.map(header => `"${updatedProduct[header] || ''}"`).join(',');
    lines[productId] = updatedLine;

    const updatedCSV = lines.join('\n');
    
    fs.writeFile('public/productos.csv', updatedCSV, (err) => {
      if (err) {
        console.error('Error escribiendo CSV:', err);
        return res.status(500).json({ error: 'Error al actualizar el producto' });
      }
      
      console.log('Producto actualizado correctamente:', updatedProduct);
      res.json({ 
        success: true, 
        message: 'Producto actualizado correctamente',
        producto: updatedProduct
      });
    });
  });
});

// API: Actualizar solo stock
app.patch('/api/productos/:id/stock', (req, res) => {
  const productId = parseInt(req.params.id);
  const newStock = parseInt(req.body.stock) || 0;
  
  console.log(`Actualizando stock del producto ID: ${productId} a: ${newStock}`);
  
  fs.readFile('public/productos.csv', 'utf8', (err, data) => {
    if (err) {
      console.error('Error leyendo CSV:', err);
      return res.status(500).json({ error: 'Error al leer el archivo CSV' });
    }

    const lines = data.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.replace(/"/g, ''));
    
    if (productId < 0 || productId >= lines.length) {
      return res.status(404).json({ error: 'Producto no encontrado' });
    }

    // Encontrar índice de la columna STOCK
    const stockIndex = headers.findIndex(h => h === 'STOCK');
    if (stockIndex === -1) {
      return res.status(400).json({ error: 'El CSV no tiene columna STOCK' });
    }

    // Actualizar solo el stock
    const values = lines[productId].split(',').map(v => v.replace(/"/g, ''));
    values[stockIndex] = newStock;
    
    // Volver a agregar comillas
    const updatedLine = values.map(v => `"${v}"`).join(',');
    lines[productId] = updatedLine;

    const updatedCSV = lines.join('\n');
    
    fs.writeFile('public/productos.csv', updatedCSV, (err) => {
      if (err) {
        console.error('Error escribiendo CSV:', err);
        return res.status(500).json({ error: 'Error al actualizar el stock' });
      }
      
      console.log('Stock actualizado correctamente:', newStock);
      res.json({ 
        success: true, 
        message: 'Stock actualizado correctamente',
        nuevoStock: newStock
      });
    });
  });
});

// API: Subir CSV actualizado
app.post('/api/upload-csv', upload.single('csv'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No se subió ningún archivo' });
    }
    
    console.log('Subiendo nuevo CSV:', req.file.originalname);
    
    // Copiar el archivo subido al directorio public
    const tempPath = req.file.path;
    const targetPath = path.join(__dirname, 'public', 'productos.csv');
    
    // Hacer backup del archivo actual
    const backupPath = path.join(__dirname, 'public', `productos_backup_${Date.now()}.csv`);
    if (fs.existsSync(targetPath)) {
      fs.copyFileSync(targetPath, backupPath);
      console.log('Backup creado:', backupPath);
    }
    
    // Mover el nuevo archivo
    fs.copyFileSync(tempPath, targetPath);
    
    // Eliminar el archivo temporal
    fs.unlinkSync(tempPath);
    
    console.log('CSV actualizado correctamente');
    res.json({ 
      success: true, 
      message: 'CSV actualizado correctamente',
      backup: backupPath
    });
  } catch (error) {
    console.error('Error subiendo CSV:', error);
    res.status(500).json({ error: 'Error al subir el CSV' });
  }
});

// Ruta para descargar el CSV
app.get('/download-csv', (req, res) => {
  const filePath = path.join(__dirname, 'public', 'productos.csv');
  if (fs.existsSync(filePath)) {
    res.download(filePath, 'productos.csv');
  } else {
    res.status(404).json({ error: 'Archivo CSV no encontrado' });
  }
});

// Ruta para crear backup del CSV
app.get('/backup-csv', (req, res) => {
  const sourcePath = path.join(__dirname, 'public', 'productos.csv');
  const backupPath = path.join(__dirname, 'public', `productos_backup_${Date.now()}.csv`);
  
  if (fs.existsSync(sourcePath)) {
    fs.copyFileSync(sourcePath, backupPath);
    res.json({ 
      success: true, 
      message: 'Backup creado correctamente',
      backupFile: path.basename(backupPath)
    });
  } else {
    res.status(404).json({ error: 'Archivo CSV no encontrado' });
  }
});

// Middleware para manejar errores 404
app.use((req, res) => {
  res.status(404).json({ error: 'Ruta no encontrada' });
});

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`=== MORANT JEWELRY SYSTEM ===`);
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
  console.log(`Página principal: http://localhost:${PORT}`);
  console.log(`Panel de administración: http://localhost:${PORT}/admin`);
  console.log(`API Productos: http://localhost:${PORT}/api/productos`);
  console.log(`Archivo CSV: http://localhost:${PORT}/productos.csv`);
  console.log(`================================`);
});