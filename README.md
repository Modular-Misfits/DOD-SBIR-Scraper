# DOD SBIR/STTR Scraper

A web application for searching and downloading DOD SBIR/STTR topics.

## Features

- Search DOD SBIR/STTR topics
- Download individual PDFs directly to your browser
- Download multiple PDFs as a ZIP file
- Pagination support
- Modern, responsive UI

## Local Development

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dodsbirsttr-scraper.git
cd dodsbirsttr-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file in the frontend directory with:
```
VITE_API_URL=http://localhost:8000/api/v1
```

4. Run the development server:
```bash
npm run dev
```

5. Open http://localhost:5173 in your browser

## Deployment

This application is configured to deploy automatically to Render when changes are pushed to the main branch.

### Manual Deployment to Render

1. Create a Render account at https://render.com
2. Create a new Web Service
3. Connect your GitHub repository
4. Use the following settings:
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Automatic Deployment

1. Get your Render API key from your Render dashboard
2. Add the API key to your GitHub repository secrets:
   - Go to your repository settings
   - Navigate to Secrets and Variables > Actions
   - Add a new secret named `RENDER_API_KEY` with your Render API key
3. Update the service ID in `.github/workflows/deploy.yml` with your Render service ID
4. Push to main branch to trigger deployment

## License

MIT