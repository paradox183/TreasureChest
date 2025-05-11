const express = require('express');
const multer = require('multer');
const pdfParse = require('pdf-parse');
const csv = require('csv-stringify');

const app = express();
const upload = multer({ storage: multer.memoryStorage() });

// Function to parse the text and extract the table
const parseTextAndExtractTable = (text) => {
    const lines = text.split('\n');
    let tableData = [];
    let inTable = false;
    let headersFound = false; // Flag to track if headers are extracted

    for (const line of lines) {
        const trimmedLine = line.trim();

        if (trimmedLine.startsWith('#') && trimmedLine.includes('Event') && trimmedLine.includes('Entries') && trimmedLine.includes('Heats') && trimmedLine.includes('Est. Start') && trimmedLine.includes('Actual Start') && !headersFound) {
            // Start of the table (and only extract headers once)
            inTable = true;
            tableData.push(trimmedLine.split(',').map(cell => cell.trim()));
            headersFound = true;
        } else if (inTable && trimmedLine.match(/^\d+\s*,/)) {
            // Inside the table, extract data rows starting with a number
            tableData.push(trimmedLine.split(',').map(cell => cell.trim()));
        } else if (inTable && trimmedLine.includes('Scheduled Break:')) {
            //  Capture scheduled breaks
            tableData.push(['', trimmedLine, '', '', trimmedLine.split(',').pop().trim(), '']); // Format break line
        } else if (inTable && trimmedLine.startsWith('68')) {
            tableData.push(trimmedLine.split(',').map(cell => cell.trim()));
        }
        else if (inTable && trimmedLine === '') {
            inTable = false;
        }
    }

    return tableData;
};


// Function to convert data to CSV
const convertToCSV = (data) => {
    return new Promise((resolve, reject) => {
        csv.stringify(data, (err, output) => {
            if (err) {
                reject(err);
            } else {
                resolve(output);
            }
        });
    });
};

app.get('/', (req, res) => {
    res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>PDF to CSV Converter</title>
    </head>
    <body>
      <h1>Upload your PDF</h1>
      <form method="POST" action="/convert" enctype="multipart/form-data">
        <input type="file" name="pdfFile" accept=".pdf" required>
        <button type="submit">Convert to CSV</button>
      </form>
    </body>
    </html>
  `);
});

app.post('/convert', upload.single('pdfFile'), async (req, res) => {
    if (!req.file) {
        return res.status(400).send('No file uploaded.');
    }

    try {
        const pdfText = await pdfParse(req.file.buffer);
        console.log('--- Raw PDF Text: ---');
        console.log(pdfText.text);

        const tableData = parseTextAndExtractTable(pdfText.text);
        console.log('\n--- Parsed Table Data: ---');
        console.log(JSON.stringify(tableData, null, 2)); // Pretty-print the table data

        if (tableData.length > 0) {
            //  Commented out CSV conversion for debugging
            //   const csvData = await convertToCSV(tableData);

            //   res.setHeader('Content-Type', 'text/csv');
            //   res.setHeader('Content-Disposition', 'attachment; filename=output.csv');
            //   return res.send(csvData);
            res.send('<pre>PDF Parsed. Check the console for output.</pre>'); // Simple response
        } else {
            return res.status(400).send('No table data found in the PDF.');
        }
    } catch (error) {
        console.error('Error processing PDF:', error);
        return res.status(500).send('Error processing PDF.');
    }
});

app.listen(3000, () => {
    console.log('Server started on http://localhost:3000');
});