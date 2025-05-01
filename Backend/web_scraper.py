```python
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import cv2
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from datetime import datetime
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed

# Load environment variables
load_dotenv()
CRIMEOMETER_API_KEY = os.getenv("CRIMEOMETER_API_KEY", "YOUR_CRIMEOMETER_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctimeuse { hasError: false, error: null };
            }

            static getDerivedStateFromError(error) {
                return { hasError: true, error };
            }

            render() {
                if (this.state.hasError) {
                    return (
                        <div className="container">
                            <h1>Something Went Wrong</h1>
                            <p className="text-center text-red-500">Error: {this.state.error && this.state.error.message ? this.state.error.message : 'Unknown error'}</p>
                            <p className="text-center">Please check the console for more details (F12 → Console) and refresh the page.</p>
                        </div>
                    );
                }
                return this.props.children;
            }
        }

        const App = () => {
            const [data, setData] = React.useState([]);
            const [status, setStatus] = React.useState('');
            const [name, setName] = React.useState('');
            const [image, setImage] = React.useState(null);
            const [identifications, setIdentifications] = React.useState([]);
            const [lat, setLat] = React.useState('37.7749');
            const [lon, setLon] = React.useState('-122.4194');
            const [startDate, setStartDate] = React.useState('2025-04-01T00:00:00');
            const [endDate, setEndDate] = React.useState('2025-04-25T23:59:59');
            const [crimeometerData, setCrimeometerData] = React.useState(null);
            const [loading, setLoading] = React.useState(true);
            const [filterSource, setFilterSource] = React.useState('All');
            const [isFetching, setIsFetching] = React.useState(false);

            React.useEffect(() => {
                setTimeout(() => setLoading(false), 1000);
            }, []);

            const fetchData = async () => {
                setIsFetching(true);
                try {
                    const response = await fetch('http://localhost:8000/data');
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const result = await response.json();
                    setData(result);
                    setStatus('Data fetched successfully');
                } catch (error) {
                    console.error('Error fetching data:', error.message);
                    setStatus(error.message.includes('Failed to fetch') ? 'Error: Backend server not running. Please start the backend on http://localhost:8000.' : `Error fetching data: ${error.message}`);
                    setData([]);
                } finally {
                    setIsFetching(false);
                }
            };

            const handleFetchData = async () => {
                setIsFetching(true);
                try {
                    const response = await fetch('http://localhost:8000/fetch-data', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const result = await response.json();
                    setStatus(result.status);
                    await fetchData();
                } catch (error) {
                    console.error('Error fetching data:', error.message);
                    setStatus(error.message.includes('Failed to fetch') ? 'Error: Backend server not running. Please start the backend on http://localhost:8000.' : `Error fetching data: ${error.message}`);
                    setData([]);
                } finally {
                    setIsFetching(false);
                }
            };

            const handleFetchCrimeometer = async () => {
                setIsFetching(true);
                const latNum = parseFloat(lat);
                const lonNum = parseFloat(lon);
                const dateFormat = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
                if (isNaN(latNum) || latNum < -90 || latNum > 90) {
                    setStatus("Error: Latitude must be a number between -90 and 90");
                    setIsFetching(false);
                    return;
                }
                if (isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
                    setStatus("Error: Longitude must be a number between -180 and 180");
                    setIsFetching(false);
                    return;
                }
                if (!dateFormat.test(startDate) || !dateFormat.test(endDate)) {
                    setStatus("Error: Dates must be in format YYYY-MM-DDThh:mm:ss");
                    setIsFetching(false);
                    return;
                }
                try {
                    const response = await fetch('http://localhost:8000/fetch-crimeometer', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            lat: latNum,
                            lon: lonNum,
                            start_date: startDate,
                            end_date: endDate,
                            distance: "1mi"
                        })
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const result = await response.json();
                    setCrimeometerData(result.data);
                    setStatus('CrimeoMeter data fetched successfully');
                    await fetchData();
                } catch (error) {
                    console.error('Error fetching CrimeoMeter data:', error.message);
                    setStatus(`Error fetching CrimeoMeter data: ${error.message}`);
                    setCrimeometerData(null);
                } finally {
                    setIsFetching(false);
                }
            };

            const handleIdentifyImage = async (e) => {
                e.preventDefault();
                if (!image) {
                    setIdentifications([{ name: "Error", details: "No image uploaded" }]);
                    return;
                }
                setIsFetching(true);
                const formData = new FormData();
                formData.append('image', image);
                try {
                    const response = await fetch('http://localhost:8000/identify/image', {
                        method: 'POST',
                        body: formData
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const result = await response.json();
                    setIdentifications(result.identifications);
                    setStatus('Image identification completed');
                } catch (error) {
                    console.error('Error identifying image:', error.message);
                    setIdentifications([{ name: "Error", details: error.message }]);
                    setStatus(`Error identifying image: ${error.message}`);
                } finally {
                    setIsFetching(false);
                }
            };

            const handleIdentifyName = async () => {
                if (!name) {
                    setIdentifications([{ name: "Error", details: "No name entered" }]);
                    return;
                }
                setIsFetching(true);
                try {
                    const response = await fetch('http://localhost:8000/identify/name', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name })
                    });
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const result = await response.json();
                    setIdentifications([result.identification]);
                    setStatus('Name identification completed');
                } catch (error) {
                    console.error('Error identifying name:', error.message);
                    setIdentifications([{ name: "Error", details: error.message }]);
                    setStatus(`Error identifying name: ${error.message}`);
                } finally {
                    setIsFetching(false);
                }
            };

            React.useEffect(() => {
                if (loading) return;

                try {
                    if (!window.THREE) {
                        console.error("Three.js failed to load");
                        return;
                    }
                    const scene = new THREE.Scene();
                    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / 384, 0.1, 1000);
                    const renderer = new THREE.WebGLRenderer();
                    renderer.setSize(window.innerWidth, 384);
                    const canvas = document.getElementById('three-canvas');
                    if (!canvas) {
                        console.error("Three.js canvas element not found");
                        return;
                    }
                    canvas.appendChild(renderer.domElement);

                    const controls = new THREE.OrbitControls(camera, renderer.domElement);
                    controls.enableDamping = true;
                    controls.dampingFactor = 0.25;
                    controls.screenSpacePanning = false;

                    const ambientLight = new THREE.AmbientLight(0x404040);
                    scene.add(ambientLight);
                    const pointLight = new THREE.PointLight(0xffffff, 1, 100);
                    pointLight.position.set(10, 10, 10);
                    scene.add(pointLight);

                    const crimeTypes = data.length > 0 ? [...new Set(data.map(d => {
                        const match = d.crime_story.match(/murder|theft|assault|robbery|arrest/i);
                        return match ? match[0] : 'Crime';
                    }))].slice(0, 5) : ['Robbery', 'Assault', 'Burglary', 'Theft', 'Vandalism'];
                    const counts = crimeTypes.map(type => data.filter(d => d.crime_story.toLowerCase().includes(type.toLowerCase())).length || Math.random() * 10);

                    const bars = [];
                    crimeTypes.forEach((type, i) => {
                        const geometry = new THREE.BoxGeometry(0.8, counts[i], 0.8);
                        const material = new THREE.MeshPhongMaterial({ color: 0x00ff00 });
                        const bar = new THREE.Mesh(geometry, material);
                        bar.position.set(i * 1.5 - crimeTypes.length * 0.75, counts[i] / 2, 0);
                        scene.add(bar);
                        bars.push(bar);
                    });

                    camera.position.z = 15;

                    const animate = () => {
                        requestAnimationFrame(animate);
                        bars.forEach(bar => {
                            bar.rotation.y += 0.01;
                        });
                        controls.update();
                        renderer.render(scene, camera);
                    };
                    animate();

                    window.addEventListener('resize', () => {
                        camera.aspect = window.innerWidth / 384;
                        camera.updateProjectionMatrix();
                        renderer.setSize(window.innerWidth, 384);
                    });

                    return () => {
                        if (canvas) {
                            canvas.innerHTML = '';
                        }
                        window.removeEventListener('resize', () => {});
                    };
                } catch (error) {
                    console.error("Three.js error:", error.message);
                }
            }, [data, loading]);

            if (loading) {
                return (
                    <div className="container">
                        <h1>Crime Data Visualizer</h1>
                        <p className="text-center">Loading...</p>
                    </div>
                );
            }

            const filteredData = filterSource === 'All' ? data : data.filter(item => item.source.includes(filterSource));

            return (
                <div className="container">
                    <h1>Crime Data Visualizer</h1>
                    {isFetching && <p className="text-center">Fetching data...</p>}
                    <div className="mb-4">
                        <button
                            onClick={handleFetchData}
                            disabled={isFetching}
                            className={isFetching ? 'bg-gray-500' : 'bg-green-500'}
                        >
                            Fetch Crime Data from Reliable Sources
                        </button>
                        <p className="mt-2">{status}</p>
                    </div>

                    <div className="mt-4">
                        <h2>Fetch Real-Time Crime Data (CrimeoMeter)</h2>
                        <div className="mb-4">
                            <label htmlFor="lat">Latitude:</label>
                            <input
                                id="lat"
                                name="lat"
                                type="text"
                                value={lat}
                                onChange={(e) => setLat(e.target.value)}
                                placeholder="e.g., 37.7749 (San Francisco)"
                                disabled={isFetching}
                            />
                        </div>
                        <div className="mb-4">
                            <label htmlFor="lon">Longitude:</label>
                            <input
                                id="lon"
                                name="lon"
                                type="text"
                                value={lon}
                                onChange={(e) => setLon(e.target.value)}
                                placeholder="e.g., -122.4194 (San Francisco)"
                                disabled={isFetching}
                            />
                        </div>
                        <div className="mb-4">
                            <label htmlFor="startDate">Start Date (YYYY-MM-DDThh:mm:ss):</label>
                            <input
                                id="startDate"
                                name="startDate"
                                type="text"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                placeholder="e.g., 2025-04-01T00:00:00"
                                disabled={isFetching}
                            />
                        </div>
                        <div className="mb-4">
                            <label htmlFor="endDate">End Date (YYYY-MM-DDThh:mm:ss):</label>
                            <input
                                id="endDate"
                                name="endDate"
                                type="text"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                placeholder="e.g., 2025-04-25T23:59:59"
                                disabled={isFetching}
                            />
                        </div>
                        <button
                            onClick={handleFetchCrimeometer}
                            className={isFetching ? 'bg-gray-500' : 'bg-purple-500'}
                            disabled={isFetching}
                        >
                            Fetch CrimeoMeter Data
                        </button>
                        {crimeometerData && (
                            <div className="bg-gray-800 p-4 rounded mt-2">
                                <h3>CrimeoMeter Results</h3>
                                <pre>{JSON.stringify(crimeometerData, null, 2)}</pre>
                            </div>
                        )}
                    </div>

                    <div className="mt-4">
                        <h2>Identify Criminal</h2>
                        <div className="mb-4">
                            <label htmlFor="imageUpload">Upload Image (JPG or PNG only):</label>
                            <input
                                id="imageUpload"
                                name="imageUpload"
                                type="file"
                                accept="image/jpeg,image/png"
                                onChange={(e) => setImage(e.target.files[0])}
                                disabled={isFetching}
                            />
                            <button
                                onClick={handleIdentifyImage}
                                className={isFetching ? 'bg-gray-500' : 'bg-blue-500'}
                                disabled={isFetching}
                            >
                                Identify by Image
                            </button>
                        </div>
                        <div className="mb-4">
                            <label htmlFor="criminalName">Enter Name:</label>
                            <input
                                id="criminalName"
                                name="criminalName"
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., John Doe"
                                disabled={isFetching}
                            />
                            <button
                                onClick={handleIdentifyName}
                                className={isFetching ? 'bg-gray-500' : 'bg-blue-500'}
                                disabled={isFetching}
                            >
                                Identify by Name
                            </button>
                        </div>
                        {identifications.length > 0 && (
                            <div className="bg-gray-800besides that, you might want to consider using a different approach for fetching data from the web. Here's an example of how you might do it:

```javascript
const fetchData = async () => {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        setData(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
};
```

This approach uses the modern Fetch API and handles errors gracefully.

Would you like me to provide more specific improvements for your code, or would you like to share more details about what you're trying to accomplish?