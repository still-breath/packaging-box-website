<div align="center">
<h1>📦 PACKAGING BOX OPTIMIZER - 3D CONTAINER PACKING SYSTEM</h1>
<a href="https://github.com/still-breath/packaging-box-optimizer.git">
    <img src="./thumbnail.png" height="300" alt="packaging-box-optimizer">
</a>
</div>

<p align="center">
<a target="_blank" href="https://www.linkedin.com/in/syahrulahmad/"><img height="20" src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" /></a>
<a target="_blank" href="https://github.com/still-breath/packaging-box-optimizer"><img height="20" src="https://img.shields.io/github/license/still-breath/packaging-box-optimizer" alt="License"></a>
<a target="_blank" href="https://github.com/still-breath/packaging-box-optimizer"><img height="20" src="https://img.shields.io/github/commit-activity/t/still-breath/packaging-box-optimizer" alt="Last Commits"></a>
<a target="_blank" href="https://github.com/still-breath/packaging-box-optimizer"><img height="20" src="https://img.shields.io/github/repo-size/still-breath/packaging-box-optimizer" alt="Repo Size"></a>
</p>

<p align="center">
<a href="#-introduction">Introduction</a> &nbsp;&bull;&nbsp;
<a href="#-tech-stack">Tech Stack</a> &nbsp;&bull;&nbsp;
<a href="#-preview">Preview</a> &nbsp;&bull;&nbsp;
<a href="#-installation--usage">Installation & Usage</a> &nbsp;&bull;&nbsp;
<a href="#-optimization-algorithms">Optimization Algorithms</a> &nbsp;&bull;&nbsp;
<a href="#-api-endpoints">API Endpoints</a> &nbsp;&bull;&nbsp;
<a href="#-issue">Issue</a>&nbsp;&bull;&nbsp;
<a href="#-license">License</a>&nbsp;&bull;&nbsp;
<a href="#-author">Author</a>
</p>

---

## 📄 Introduction

This project is a **3D container packing optimization system** designed to solve the complex problem of efficiently packing various boxes into containers. The application combines multiple optimization algorithms with **real-time 3D visualization** to provide the best packing solutions for logistics and warehouse management.

### 🎯 Key Features
- **Multiple Algorithms**: Various optimization algorithms including Gurobi, Genetic Algorithm, and Heuristic methods
- **3D Visualization**: Real-time interactive 3D rendering of packing solutions
- **Container Analysis**: Detailed statistics including fill rate, weight distribution, and space utilization
- **Group Management**: Organize boxes by categories with color-coded visualization
- **Performance Metrics**: Calculate efficiency, weight optimization, and space usage
- **Interactive Controls**: Scene settings with customizable display options
- **Export Results**: Generate reports and export packing configurations

This project demonstrates advanced **operations research** techniques combined with modern web technologies for solving real-world logistics optimization problems.

---

## 💻 Tech Stack

Frameworks, Libraries, and Tools used in this project:

<p align="center">
<a target="_blank" href="https://reactjs.org/">
<img height="30" src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"/>
</a>
<a target="_blank" href="https://threejs.org/">
<img height="30" src="https://img.shields.io/badge/Three.js-000000?style=for-the-badge&logo=three.js&logoColor=white" alt="Three.js"/>
</a>
<a target="_blank" href="https://www.typescriptlang.org/">
<img height="30" src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript"/>
</a>
<a target="_blank" href="https://vitejs.dev/">
<img height="30" src="https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E" alt="Vite"/>
</a>
</p>

<p align="center">
<a target="_blank" href="https://www.python.org/">
<img height="30" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
</a>
<a target="_blank" href="https://fastapi.tiangolo.com/">
<img height="30" src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white" alt="FastAPI"/>
</a>
<a target="_blank" href="https://www.gurobi.com/">
<img height="30" src="https://img.shields.io/badge/Gurobi-FF6600?style=for-the-badge&logoColor=white" alt="Gurobi"/>
</a>
<a target="_blank" href="https://numpy.org/">
<img height="30" src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy"/>
</a>
</p>

<p align="center">
<a target="_blank" href="https://pandas.pydata.org/">
<img height="30" src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas"/>
</a>
<a target="_blank" href="https://docs.pydantic.dev/">
<img height="30" src="https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logoColor=white" alt="Pydantic"/>
</a>
<a target="_blank" href="https://www.uvicorn.org/">
<img height="30" src="https://img.shields.io/badge/Uvicorn-2B5F3F?style=for-the-badge&logoColor=white" alt="Uvicorn"/>
</a>
</p>

---

## 🖼️ Preview

<div align="center">
<img src="./preview.png" alt="Packaging Box Optimizer 3D Visualization" width="80%">
</div>

### 📊 Application Features
- **3D Container Visualization**: Interactive 3D rendering of packed containers with realistic box representations
- **Real-time Statistics**: Live calculation of fill rates, weight distribution, and space utilization
- **Group Management**: Color-coded box categories for easy identification and organization
- **Scene Controls**: Customizable display options including container edges, goods visibility, and lighting

### 🎯 Optimization Capabilities
- **Multiple Algorithms**: Choose from various optimization strategies
- **Constraint Handling**: Weight limits, dimensional constraints, and stacking rules
- **Performance Analysis**: Detailed metrics on packing efficiency and space usage
- **Export Functions**: Save configurations and generate optimization reports

### 📈 Performance Metrics
- **Fill Rate**: Up to 88.5% container utilization shown in example
- **Algorithm Speed**: Sub-second optimization for medium-sized problems
- **3D Rendering**: 60 FPS smooth visualization with WebGL
- **Scalability**: Handles containers with 100+ boxes efficiently

---

## ⚙️ Installation & Usage

### 📋 Prerequisites
- Python 3.8 or higher
- Node.js (LTS version recommended)
- Git (optional, for repository cloning)
- Gurobi license (academic license available for free)

### 🔧 Step-by-Step Installation

#### 1. Clone Repository
```bash
# Clone the repository
git clone https://github.com/still-breath/packaging-box-optimizer.git
cd packaging-box-optimizer
```

#### 2. Backend Setup (Python/FastAPI)
```bash
# Navigate to backend directory
cd storage-backend/python

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Frontend Setup (React)
```bash
# Navigate to frontend directory (new terminal)
cd storage-manager

# Install Node.js dependencies
npm install
# or if using Yarn:
# yarn install
```

#### 4. Gurobi License Setup
```bash
# For academic users, get free license at:
# https://www.gurobi.com/academia/academic-program-and-licenses/

# Install license file (gurobi.lic) in your home directory
# or set GUROBI_LICENSE_FILE environment variable
```

### 🚀 Usage

#### 1. Start Backend Server
```bash
# From storage-backend/python directory with venv activated
uvicorn main:app --reload --port 8000

# Server will be available at: http://localhost:8000
```

#### 2. Start Frontend Server
```bash
# From storage-manager directory
npm start
# or
yarn start

# Application will open at: http://localhost:3000 or http://localhost:5173
```

#### 3. Using the Application
1. **Select Container**: Choose preset container or define custom dimensions
2. **Add Boxes**: Define box groups with dimensions and quantities
3. **Choose Algorithm**: Select optimization algorithm (Gurobi, Genetic Algorithm, etc.)
4. **Calculate**: Click "Calculate & Visualize" to generate packing solution
5. **Analyze**: Review 3D visualization and performance metrics
6. **Export**: Save results and configurations

### 📁 Project Structure
```
packaging-box-optimizer/
├── storage-backend/          # Backend services
│   └── python/              # FastAPI backend
│       ├── main.py          # Main FastAPI application
│       ├── algorithms/      # Optimization algorithms
│       ├── models/          # Data models
│       └── requirements.txt # Python dependencies
├── storage-manager/         # React frontend
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   ├── services/        # API services
│   │   └── utils/           # Utility functions
│   ├── public/              # Static assets
│   └── package.json         # Node.js dependencies
├── docs/                    # Documentation
└── README.md
```

---

## 🧠 Optimization Algorithms

### 🎯 Available Algorithms

#### 1. **Gurobi Optimizer**
- **Type**: Mixed-Integer Programming (MIP)
- **Performance**: Optimal solutions for small to medium problems
- **Complexity**: O(2^n) worst case, but highly optimized
- **License**: Academic license required

#### 2. **Genetic Algorithm**
- **Type**: Metaheuristic evolutionary algorithm
- **Performance**: Near-optimal solutions for large problems
- **Complexity**: O(generations × population_size × n)
- **Advantages**: No license required, handles large datasets

#### 3. **Greedy Heuristic**
- **Type**: Constructive heuristic
- **Performance**: Fast approximate solutions
- **Complexity**: O(n log n)
- **Use Case**: Quick estimates and baseline comparisons

#### 4. **Bin Packing Variants**
- **First Fit**: Simple and fast
- **Best Fit**: Better space utilization
- **First Fit Decreasing**: Sorted input for improved results

### 🔧 Algorithm Configuration
```python
# Example algorithm parameters
{
    "algorithm": "gurobi",
    "time_limit": 300,          # seconds
    "gap_tolerance": 0.01,      # 1% optimality gap
    "constraints": {
        "weight_limit": 1000,   # kg
        "stack_height": 5,      # max boxes per stack
        "fragile_items": true   # special handling
    }
}
```

---

## 🚩 Issue

If you encounter bugs or have problems, please report them by opening a **new issue** in this repository.

### 📋 Issue Template
When reporting issues, please include:
- Problem description and expected behavior
- Steps to reproduce the issue
- Environment details (OS, Python version, Node.js version)
- Algorithm used and input parameters
- Error logs and screenshots
- Container and box specifications

### 🔍 Common Issues and Solutions

#### Gurobi License Issues:
- **License not found**: Set GUROBI_LICENSE_FILE environment variable
- **License expired**: Renew academic license or contact Gurobi support
- **Installation problems**: Use `pip install gurobipy` and verify installation

#### Performance Issues:
- **Slow optimization**: Reduce problem size or increase time limits
- **Memory errors**: Use simpler algorithms for large datasets
- **3D rendering lag**: Update graphics drivers or reduce visualization complexity

#### API Connection Issues:
- **CORS errors**: Verify backend is running on port 8000
- **Request timeout**: Increase timeout limits for complex optimizations
- **JSON parsing errors**: Validate input data format

#### Frontend Issues:
- **3D visualization not loading**: Check WebGL support in browser
- **Build errors**: Clear npm cache and reinstall dependencies
- **React warnings**: Update to latest stable versions

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 📌 Author

<div align="center">
<h3>🧑‍💻 Syahrul Fathoni Ahmad</h3>
<p><em>Operations Research Engineer | 3D Visualization Specialist | Logistics Optimization Expert</em></p>

<p>
<a target="_blank" href="https://www.linkedin.com/in/syahrulahmad/">
<img height="25" src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="linkedin" />
</a>
<a target="_blank" href="https://github.com/still-breath">
<img height="25" src="https://img.shields.io/badge/Github-000000?style=for-the-badge&logo=github&logoColor=white" alt="github"/>
</a>
<a target="_blank" href="https://syahrul-fathoni.vercel.app">
<img height="25" src="https://img.shields.io/badge/Portfolio-00BC8E?style=for-the-badge&logo=googlecloud&logoColor=white" alt="portfolio"/>
</a>
</p>
</div>

---

<div align="center">
<p><strong>⭐ If this project is helpful, don't forget to give it a star!</strong></p>
<p><em>Created with ❤️ for advancing logistics optimization and 3D visualization technology</em></p>
</div>