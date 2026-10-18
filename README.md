# Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Group R-26-IT-021**  
**Faculty of Computing, SLIIT**  

**Project Title:** Intelligent Ayurvedic Herbal Plant Identification and Economic Analysis in Sri Lanka

**Team Members:**
- **M P Munasinghe** – Herbal Knowledge Intelligence System (RAG-based AI assistant)
- **D G T K Wickramasinghe** – AI-Driven Cultivation Recommendation System
- **H D Sachintha** – Mobile-Based Ayurvedic Plant Detection using Image Recognition
- **P A H K Pattiya Arachchi** – Explainable AI System for Medicinal Plant Quality Assessment

---

## Abstract

The declining availability of traditional Ayurvedic knowledge, the rising demand for medicinal plants, and the challenges faced by farmers in selecting suitable crops have created a need for intelligent digital decision-support systems. This research presents an integrated AI-powered platform for medicinal plant identification, cultivation guidance, knowledge retrieval, and quality assessment in the Sri Lankan context.

The proposed system combines computer vision, explainable AI, retrieval-augmented generation, and machine learning to support farmers, Ayurvedic practitioners, students, and manufacturers. It includes a mobile-based plant recognition module, a conversational herbal knowledge assistant, an AI-based cultivation recommendation system, and a quality assessment model that classifies plant condition using image analysis. By improving plant selection, cultivation planning, and access to reliable herbal information, the system contributes to sustainable agricultural practices, economic productivity, and preservation of indigenous medical knowledge.

---

## Problem Statement

Sri Lanka possesses a rich heritage of traditional Ayurvedic medicine and a diverse range of medicinal plant species; however, this knowledge is rapidly decreasing due to limited digital access, low awareness among younger generations, and the ageing population of traditional practitioners. Farmers also face significant losses because they often choose crops without adequate information about soil suitability, climate conditions, market demand, and cultivation requirements. In addition, inconsistent plant quality and the lack of accessible, context-aware guidance reduce productivity and increase dependence on imported raw materials.

This creates a clear need for an intelligent and user-friendly system that can support plant recognition, cultivation planning, educational guidance, and quality assessment using AI-driven decision support.

---

## Research Objectives

The primary objectives of this study are as follows:

1. To design and implement an AI-based system for identifying medicinal plants using image data and plant characteristics.
2. To provide a conversational knowledge assistant that enables users to access Ayurvedic plant information quickly and accurately.
3. To develop a cultivation recommendation component that recommends suitable crops based on environmental, soil, and economic factors.
4. To integrate explainable visual quality assessment for evaluating plant health and maturity.
5. To support sustainable agricultural decision-making for farmers and stakeholders in the medicinal plant industry.

---

## Research Questions

1. How can AI techniques improve medicinal plant identification in Sri Lanka?
2. How can a conversational system provide reliable and context-aware Ayurvedic knowledge?
3. How can cultivation recommendations support farmers in selecting profitable and suitable crops?
4. How can explainable AI improve trust and usability in plant quality assessment?

---

## Scope of the Study

This project focuses on the development of an integrated AI-based ecosystem for medicinal plant-related decision support. The scope includes:

- Image-based identification of medicinal plants using deep learning
- Retrieval-augmented conversational AI for herbal knowledge support
- Cultivation planning based on land conditions, climate, soil, and budget
- Quality assessment of plant health using explainable AI methods
- A mobile and web-based user interface for access by farmers, students, and practitioners

The research is targeted towards Sri Lankan medicinal plants and is designed to be practical, scalable, and suitable for future extension.

---

## Proposed Solution

The system is designed as a four-module architecture:

1. **Mobile-Based Plant Detection Module** – Uses a CNN-based model to identify medicinal plants from leaf and flower images.
2. **Herbal Knowledge Intelligence Module** – Provides contextual answers through a RAG-based AI assistant that combines a knowledge base with retrieval-based reasoning.
3. **AI-Driven Cultivation Recommendation Module** – Recommends suitable plants based on soil type, rainfall, humidity, temperature, budget, and land size.
4. **Explainable Quality Assessment Module** – Uses ResNet50 and Grad-CAM to evaluate whether a plant is healthy, diseased, or overmature and presents visual explanations to the user.

---

## Cultivation Recommendation Component

The cultivation recommendation component is a key part of the system and addresses the need for data-driven agricultural planning. The component allows users to enter environmental and farm-related details such as temperature, humidity, rainfall, soil pH, soil type, land size, irrigation method, growing season, and budget. Based on this input, the system applies a trained machine learning model to recommend the most suitable medicinal plants and estimates their profitability and cultivation viability. Soil photos can also be classified into one of the four soil classes included in the bundled image dataset.

This feature supports farmers in making practical planting decisions, reducing crop failure, and improving productivity. The recommendation logic combines both agronomic factors and economic considerations, making the output relevant to real-world cultivation planning.

The platform interface presents this process through a structured cultivation page that guides the user step by step and displays recommendation results clearly. The design emphasises usability, accessibility, and decision support for non-technical users in the agricultural domain.

---

## Methodology

The research follows a practical software engineering and AI development methodology. The workflow includes dataset preparation, model training, system integration, evaluation, and interface design.

- **Data Collection:** Medicinal plant cultivation and agricultural data were gathered from domain sources and structured datasets.
- **Preprocessing:** Data were cleaned, transformed, and prepared for machine learning models.
- **Model Development:** Prediction models were trained and evaluated to identify suitable cultivation conditions and crop recommendations.
- **System Integration:** Model outputs were connected to a Flutter-based frontend and backend services.
- **Validation:** The recommendation results were reviewed for relevance, accuracy, and usability within the application.

---

## Technologies Used

| Module | Technologies |
|--------|--------------|
| Plant Detection | CNN, TensorFlow, OpenCV, Flutter |
| Knowledge Assistant | RAG, ChromaDB, OpenAI embeddings, Flask |
| Cultivation Recommendation | Random Forest, Gradient Boosting, Python, Flask |
| Quality Assessment | ResNet50, Grad-CAM, PyTorch, OpenCV |
| Frontend | Flutter |
| Backend & Data Handling | Python, Flask, SQLite/ChromaDB, CSV-based datasets |

---

## Expected Outcomes

This project aims to deliver a practical and intelligent digital platform that bridges the gap between traditional Ayurvedic knowledge and modern AI technology. It is expected to improve medicinal plant identification, strengthen cultivation decision-making, support accessible knowledge retrieval, and assist in the quality assessment of plant materials.

By combining AI and agricultural intelligence, the system contributes to both academic research and real-world value for farmers, health practitioners, students, and the wider medicinal plant sector in Sri Lanka.

---

## Conclusion

The intelligent Ayurvedic plant ecosystem proposed in this research offers a modern solution to several longstanding problems in the medicinal plant domain. By integrating image recognition, explainable AI, retrieval-based knowledge support, and cultivation recommendation, the system creates a holistic approach to sustainable plant management and traditional knowledge preservation.

The cultivation recommendation component, in particular, plays a critical role in helping users choose crops that match their environmental and economic conditions, ensuring more informed and productive agricultural decisions.
