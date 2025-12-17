#!/usr/bin/env python3
"""
FastAPI Backend for ThreatVision Preview UI
"""
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from database.models import get_session
from monitors.cve_monitor import CVEMonitor
from monitors.github_monitor import GithubMonitor
from database.models import CVERecord, Repository
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("api")

# Create FastAPI app
app = FastAPI(
    title="ThreatVision API",
    description="API for ThreatVision Preview UI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="ui"), name="static")

# Initialize monitors to get database engines
cve_monitor = CVEMonitor()
github_monitor = GithubMonitor()

@app.get("/api/reports")
async def get_reports():
    """Get list of available reports"""
    try:
        # Get all report directories
        reports = []
        
        if os.path.exists(Config.DATA_DIR):
            for year in os.listdir(Config.DATA_DIR):
                year_path = os.path.join(Config.DATA_DIR, year)
                if os.path.isdir(year_path):
                    for date in os.listdir(year_path):
                        date_path = os.path.join(year_path, date)
                        if os.path.isdir(date_path):
                            report_file = os.path.join(date_path, f"Daily_{date}.md")
                            if os.path.exists(report_file):
                                reports.append({
                                    "date": date,
                                    "year": year,
                                    "path": report_file,
                                    "url": f"/api/reports/{date}"
                                })
        
        # Sort reports by date (newest first)
        reports.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "total": len(reports),
            "reports": reports
        }
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/reports/{date}")
async def get_report(date: str):
    """Get report for a specific date"""
    try:
        # Parse date to get year
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d")
            year = report_date.strftime("%Y")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        report_file = os.path.join(Config.DATA_DIR, year, date, f"Daily_{date}.md")
        
        if not os.path.exists(report_file):
            raise HTTPException(status_code=404, detail="Report not found")
        
        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "date": date,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report {date}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/cves")
async def get_cves(limit: int = 20, offset: int = 0):
    """Get list of CVEs"""
    try:
        session = get_session(cve_monitor.engine)
        try:
            cves = session.query(CVERecord).order_by(CVERecord.publish_time.desc()).offset(offset).limit(limit).all()
            
            result = []
            for cve in cves:
                result.append({
                    "id": cve.id,
                    "cve_id": cve.cve_id,
                    "description": cve.description,
                    "cvss_score": cve.cvss_score,
                    "publish_time": cve.publish_time.isoformat() if cve.publish_time else None,
                    "ai_analysis": cve.ai_analysis,
                    "is_high_value": cve.is_high_value
                })
            
            total = session.query(CVERecord).count()
            
            return {
                "total": total,
                "cves": result
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting CVEs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/cves/{cve_id}")
async def get_cve(cve_id: str):
    """Get CVE by ID"""
    try:
        session = get_session(cve_monitor.engine)
        try:
            cve = session.query(CVERecord).filter(CVERecord.cve_id == cve_id).first()
            
            if not cve:
                raise HTTPException(status_code=404, detail="CVE not found")
            
            return {
                "id": cve.id,
                "cve_id": cve.cve_id,
                "description": cve.description,
                "cvss_score": cve.cvss_score,
                "publish_time": cve.publish_time.isoformat() if cve.publish_time else None,
                "ai_analysis": cve.ai_analysis,
                "is_high_value": cve.is_high_value
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CVE {cve_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/repos")
async def get_repos(limit: int = 20, offset: int = 0):
    """Get list of repositories"""
    try:
        session = get_session(github_monitor.engine)
        try:
            repos = session.query(Repository).order_by(Repository.stars.desc()).offset(offset).limit(limit).all()
            
            result = []
            for repo in repos:
                result.append({
                    "id": repo.id,
                    "name": repo.name,
                    "url": repo.url,
                    "description": repo.description,
                    "stars": repo.stars,
                    "last_updated": repo.last_updated.isoformat() if repo.last_updated else None,
                    "ai_analysis": repo.ai_analysis,
                    "is_high_value": repo.is_high_value
                })
            
            total = session.query(Repository).count()
            
            return {
                "total": total,
                "repos": result
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting repositories: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/repos/{id}")
async def get_repo(id: int):
    """Get repository by ID"""
    try:
        session = get_session(github_monitor.engine)
        try:
            repo = session.query(Repository).filter(Repository.id == id).first()
            
            if not repo:
                raise HTTPException(status_code=404, detail="Repository not found")
            
            return {
                "id": repo.id,
                "name": repo.name,
                "url": repo.url,
                "description": repo.description,
                "stars": repo.stars,
                "last_updated": repo.last_updated.isoformat() if repo.last_updated else None,
                "ai_analysis": repo.ai_analysis,
                "is_high_value": repo.is_high_value
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository {id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=Config.UI_PORT,
        reload=True
    )