const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

const app = express();
const PORT = process.env.PORT || 3000;

// Configuración de multer para subir imágenes
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    // Crear carpetas según categoría si no existen
    const categoria = req.body.categoria || 'otros';
    const uploadPath = path.join(__dirname, 'public', 'imagenes', categoria.toUpperCase());
    
    if (!fs.existsSync(uploadPath)) {
      fs.mkdirSync(uploadPath, { recursive: true });
    }
    
    cb(null, uploadPath);
  },
  filename: function (req, file, cb) {
    // Nombre único para la imagen
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage: storage,
  fileFilter: function (req, file, cb) {
    // Aceptar solo imágenes
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Solo se permiten archivos de imagen'));
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

// API: Agregar nuevo producto
app.post('/api/productos', upload.single('imagen'), (req, res) => {
  try {
    const nuevoProducto = {
      NOMBRE: req.body.nombre,
      CATEGORIA: req.body.categoria,
      DESCRIPCION: req.body.descripcion,
      MATERIAL: req.body.material,
      PRECIO: req.body.precio,
      MEDIDAS: req.body.medidas,
      DIAMETRO: req.body.diametro,
      LONGITUD: req.body.longitud,
      LARGO: req.body.largo,
      PAGINA: req.body.pagina,
      IMAGEN: req.file ? req.file.filename : '',
      RUTA_IMAGEN: req.file ? `/imagenes/${req.body.categoria.toUpperCase()}/${req.file.filename}` : '',
      TIPO_IMAGEN: req.file ? req.file.mimetype.split('/')[1] : ''
    };

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
  
  fs.readFile('public/productos.csv', 'utf8', (err, data) => {
    if (err) {
      console.error('Error leyendo CSV:', err);
      return res.status(500).json({ error: 'Error al leer el archivo CSV' });
    }

    const lines = data.trim().split('\n');
    const headers = lines[0];
    
    // Mantener todas las líneas excepto la que corresponde al ID
    const newLines = [headers];
    for (let i = 1; i < lines.length; i++) {
      if (i !== productId) { // El índice 1 corresponde al primer producto
        newLines.push(lines[i]);
      }
    }

    const updatedCSV = newLines.join('\n');
    
    fs.writeFile('public/productos.csv', updatedCSV, (err) => {
      if (err) {
        console.error('Error escribiendo CSV:', err);
        return res.status(500).json({ error: 'Error al eliminar el producto' });
      }
      
      res.json({ 
        success: true, 
        message: 'Producto eliminado correctamente' 
      });
    });
  });
});

// API: Actualizar producto
app.put('/api/productos/:id', upload.single('imagen'), (req, res) => {
  const productId = parseInt(req.params.id);
  
  fs.readFile('public/productos.csv', 'utf8', (err, data) => {
    if (err) {
      console.error('Error leyendo CSV:', err);
      return res.status(500).json({ error: 'Error al leer el archivo CSV' });
    }

    const lines = data.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.replace(/"/g, ''));
    
    if (productId < 1 || productId >= lines.length) {
      return res.status(404).json({ error: 'Producto no encontrado' });
    }

    // Construir objeto actualizado
    const updatedProduct = {};
    headers.forEach(header => {
      if (req.body[header.toLowerCase()] !== undefined) {
        updatedProduct[header] = req.body[header.toLowerCase()];
      } else if (req.body[header] !== undefined) {
        updatedProduct[header] = req.body[header];
      }
    });

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
      
      res.json({ 
        success: true, 
        message: 'Producto actualizado correctamente',
        producto: updatedProduct
      });
    });
  });
});

// Ruta para descargar el CSV
app.get('/download-csv', (req, res) => {
  const filePath = path.join(__dirname, 'public', 'productos.csv');
  res.download(filePath, 'productos.csv');
});

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`Servidor corriendo en http://localhost:${PORT}`);
  console.log(`Página principal: http://localhost:${PORT}`);
  console.log(`Panel de administración: http://localhost:${PORT}/admin`);
});