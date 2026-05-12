# Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Group R-26-IT-021**  
**Faculty of Computing, SLIIT**  

**Project Title:** Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Team Members:**
- **M P Munasinghe**  – Herbal Knowledge Intelligence System (RAG-based AI Assistant)
- **D G T K Wickramasinghe**  – AI-Driven Cultivation Recommendation System
- **H D Sachintha**  – Mobile-Based Ayurvedic Plant Detection using Image Recognition
- **P A H K Pattiya Arachchi**  – Explainable AI System for Medicinal Plant Quality Assessment


---

## Abstract

Sri Lanka is home to over 1,400 medicinal plant species used in Ayurveda for more than 3,000 years. However, indigenous knowledge is rapidly disappearing, farmers face significant income loss due to poor plant selection and quality issues, and the younger generation has limited access to reliable information. 

This project develops an **integrated AI-powered ecosystem** that addresses the entire medicinal plant value chain — from accurate plant identification and quality assessment to knowledge dissemination and cultivation recommendations with economic analysis. The system combines Computer Vision (CNN & ResNet50), Explainable AI (Grad-CAM), Retrieval-Augmented Generation (RAG), and Machine Learning to support farmers, Ayurvedic practitioners, students, and manufacturers.

---

## Problem Statement

- Rapid loss of traditional Ayurvedic knowledge (most practitioners aged 55+)
- Less than 30% of the population can identify common medicinal plants
- High crop failure rates (15-25%) and income loss (30-60%) for farmers
- Inconsistent raw material quality and heavy reliance on imports (LKR 2.3 Billion annually)
- Lack of accessible, multilingual, and context-aware digital tools

---

## Proposed Solution

An integrated platform consisting of four interconnected modules:

1. **Mobile-Based Plant Detection** – CNN model for real-time identification of Sri Lankan Ayurvedic plants from leaf/flower images.
2. **Herbal Knowledge Intelligence System** – Context-aware RAG-based conversational AI assistant supporting English and Sinhala.
3. **AI-Driven Cultivation Recommendation System** – Recommends suitable & profitable medicinal plants based on soil, climate, and market data.
4. **Explainable AI Quality Assessment** – Evaluates plant suitability (Healthy / Diseased / Overmature) using ResNet50 + Grad-CAM heatmaps.

---

## Key Features

- **Multi-modal AI** combining image recognition, quality assessment, and conversational intelligence
- **Explainable AI** using Grad-CAM heatmaps for transparency
- **Context-aware conversations** with session memory
- **Multilingual support** (English & Sinhala)
- **Farmer-friendly recommendations** with economic analysis
- **Scalable architecture** for adding new plants and features

---

## Technologies Used

| Module | Technologies |
|--------|--------------|
| Plant Detection | CNN, TensorFlow / PyTorch, OpenCV, Mobile (Flutter/React Native) |
| Knowledge Assistant | RAG, OpenAI embeddings (`text-embedding-3-large`), ChromaDB, GPT-4.0-mini, Flask |
| Cultivation Recommendation | Random Forest, Gradient Boosting, Python, Flask |
| Quality Assessment | ResNet50 (Transfer Learning), Grad-CAM, PyTorch, OpenCV |
| Frontend | Flutter  |
| Other | Python, Google Colab, Git |

---

