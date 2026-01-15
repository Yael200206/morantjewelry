const express = require('express');
const serverless = require('serverless-http'); // Importante
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const csv = require('csv-parser');

const app = express();

// IMPORTANTE: En Netlify, el storage local (/tmp) es volátil
const upload = multer({ dest: '/tmp/' }); 

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Las rutas deben apuntar a la base de la función /.netlify/functions/api
const router = express.Router();

router.get('/productos', (req, res) => {
  const productos = [];
  // Ruta absoluta para el CSV en Netlify
  const csvPath = path.join(__dirname, '../public/productos.csv');
  
  fs.createReadStream(csvPath)
    .pipe(csv())
    .on('data', (row) => productos.push(row))
    .on('end', () => res.json(productos))
    .on('error', () => res.status(500).json({ error: 'Error al leer CSV' }));
});

// ... Copia aquí el resto de tus rutas (POST, DELETE, PUT) ...
// Pero asegúrate de usar 'router.post', 'router.put', etc.


app.use('/.netlify/functions/api', router);

// Exportar para Netlify
module.exports = app;
module.exports.handler = serverless(app);