MAKE SURE YOU HAVE OLLAMA UP AND RUNNING, LM STUDIO ALSO WORKS. RUN WEBINTERFACE 6 IF THAT'S THE CASE
REPLACE THE VARIABLES IN THE PYTHON AND PAGE FILES AS REQUIRED
MAKE SURE YOU HAVE NPM SET UP AND WORKING

RUN ALL THIS:


For the frontend:
npm install @heroicons/react 
npm install next react react-dom 
npm install -D tailwindcss postcss autoprefixer 
npx tailwindcss init -p 
cd frontend 
npm run dev 


For the backend:
pip install -r requirements.txt
python webinterface7.py
python ollamamonitor.py


by default, the main app will run on http://127.0.0.1:5000 and the ollamatracker will run on http://127.0.0.1:7000
