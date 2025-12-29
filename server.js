const express = require('express');
const { GoogleGenerativeAI } = require("@google/generative-ai");
const path = require('path');
const cors = require('cors');

const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(cors());

const genAI = new GoogleGenerativeAI(process.env.GEMINI_KEY);

// Раздаем index.html из корня
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/api/chat', async (req, res) => {
    try {
        const { message, image, history } = req.body;
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
        const chat = model.startChat({ history: history || [] });
        
        let content = [message];
        if (image) {
            content = [{ inlineData: { data: image.split(',')[1], mimeType: "image/jpeg" } }, message];
        }

        const result = await chat.sendMessage(content);
        res.json({ text: result.response.text() });
    } catch (e) {
        console.error(e);
        res.status(500).json({ error: "API Error" });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on ${PORT}`));
