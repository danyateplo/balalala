const express = require('express');
const { GoogleGenerativeAI } = require("@google/generative-ai");
const path = require('path');
const cors = require('cors');

const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(cors());

// Ключ берется из настроек Render.com (Environment Variables)
const genAI = new GoogleGenerativeAI(process.env.GEMINI_KEY);

// Раздаем главный файл интерфейса прямо из корня
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/api/chat', async (req, res) => {
    try {
        const { message, image, history } = req.body;
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

        const chat = model.startChat({ history: history || [] });
        let parts = [message];
        
        if (image) {
            parts = [{ inlineData: { data: image.split(',')[1], mimeType: "image/jpeg" } }, message];
        }

        const result = await chat.sendMessage(parts);
        const response = await result.response;
        res.json({ text: response.text() });
    } catch (error) {
        res.status(500).json({ error: "Ошибка API" });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server started on port ${PORT}`));
