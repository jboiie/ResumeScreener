# 🔍 Resume Screener

**AI-powered candidate shortlisting — paste a job description, get your top candidates in seconds.**

A self-contained microservice that uses semantic AI search to rank your entire CV database against any job description. Runs 100% on your own server. No cloud storage. No data leaves your network except one API call to an AI provider for reranking.

---

## Table of Contents

1. [How It Works (30-second version)](#how-it-works)
2. [System Requirements](#system-requirements)
3. [First-Time Setup](#first-time-setup)
4. [Loading Your CVs (Indexing)](#loading-your-cvs-indexing)
5. [Starting & Stopping the Service](#starting--stopping-the-service)
6. [For HR: How to Use](#for-hr-how-to-use)
7. [ERP Integration Guide](#erp-integration-guide)
   - [Authentication](#authentication)
   - [API Reference](#api-reference)
   - [Code Examples](#code-examples)
   - [Integration Patterns](#integration-patterns)
   - [Error Reference](#error-reference)
8. [Configuration Reference](#configuration-reference)
9. [Updating CVs](#updating-cvs)
10. [Monitoring & Health](#monitoring--health)
11. [Troubleshooting](#troubleshooting)
12. [Architecture](#architecture)
13. [FAQ](#faq)

---

## How It Works

```
HR pastes a Job Description
          │
          ▼
  Resume Screener API
          │
          ├─ 1. Converts JD to a semantic vector (AI math, on your server)
          ├─ 2. Finds the 30 most similar CV chunks in the database
          ├─ 3. Deduplicates to unique candidates
          └─ 4. Asks Groq/Gemini AI to rank and explain the top matches
          │
          ▼
  Returns top 5–10 candidates with name, score, and reasoning
```

The entire CV database is stored locally. Only the final ranking step contacts an external AI provider (Groq or Gemini), and only the text of ~10 candidate summaries is sent — never the full CVs.

---

## System Requirements

| Requirement | Minimum | Notes |
|---|---|---|
| **Docker** | Docker Desktop 4.x+ | [Download here](https://www.docker.com/products/docker-desktop/) |
| **RAM** | 4 GB | 2 GB for Qdrant + 1.5 GB for the API + OS overhead |
| **Disk** | 5 GB free | ~1 GB for Docker images, rest for CV storage |
| **CPU** | Any modern CPU | No GPU required |
| **Internet** | Outbound HTTPS | Only needed for: initial setup (pull images), AI reranking calls |
| **OS** | Windows / Linux / macOS | All supported |

> **Already have Docker?** Check your version: `docker --version` and `docker compose version`

---

## First-Time Setup

This is a one-time process. Follow these steps in order.

### Step 1 — Get the project files

```bash
# Clone the repository
git clone https://github.com/aggamsingh/ResumeScreener.git
cd ResumeScreener
```

### Step 2 — Create your configuration file

```bash
# Copy the template
cp .env.example .env
```

Now open `.env` in any text editor (Notepad, VS Code, etc.) and fill in:

```env
# Your Groq API key (get a free one at https://console.groq.com)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# A secret key your ERP will use to authenticate — make this long and random
API_KEY=my-super-secret-key-change-this

# Where your CV files are stored (use forward slashes even on Windows)
CV_FOLDER_PATH=./cvs
```

**That's it.** Those are the only 3 values you must set.

### Step 3 — Build the Docker image

```bash
docker compose build
```

This downloads the AI embedding model and all dependencies. Takes 5–15 minutes on first run depending on your internet speed. **Only needed once.**

---

## Loading Your CVs (Indexing)

Indexing reads your CV files, converts them to AI vectors, and stores them in the database. You must do this before the screening API will return any results.

### Drop your CVs in the folder

Copy your CV files (`.pdf` or `.docx`) into the `cvs/` folder, or update `CV_FOLDER_PATH` in `.env` to point to your existing CV storage location.

```
cvs/
├── john_doe_backend_engineer.pdf
├── jane_smith_data_analyst.docx
├── raj_kumar_fullstack.pdf
└── ... (any number of files, subdirectories supported)
```

### Run the indexer

```bash
docker compose run --rm indexer
```

You'll see progress in the terminal:

```
2024-01-15 10:23:01 | INFO     | Found 20,000 CV files to process
2024-01-15 10:23:01 | INFO     | ✓  john_doe.pdf → 'John Doe' (8 chunks)
2024-01-15 10:23:02 | INFO     | ✓  jane_smith.docx → 'Jane Smith' (6 chunks)
...
2024-01-15 10:45:22 | INFO     | Indexing Complete (1340.2s)
2024-01-15 10:45:22 | INFO     |   Scanned  : 20000
2024-01-15 10:45:22 | INFO     |   Indexed  : 20000
2024-01-15 10:45:22 | INFO     |   Skipped  : 0
2024-01-15 10:45:22 | INFO     |   Failed   : 3
```

**Indexing 20,000 CVs takes approximately 20–40 minutes** (CPU-only, varies by CV length).

> 💡 **Subsequent runs are fast.** The indexer tracks which files have changed using MD5 hashes. On re-run, only new or modified CVs are processed. A run with no changes completes in seconds.

---

## Starting & Stopping the Service

### Start the service (runs in background)

```bash
docker compose up -d
```

The service is ready when the health check passes. Check status:

```bash
docker compose ps
```

You should see both `resume_screener_qdrant` and `resume_screener_api` showing **healthy**.

### Verify it's working

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "model_loaded": true,
  "version": "1.0.0"
}
```

### Stop the service

```bash
docker compose down
```

Your CV database is preserved in a Docker volume. Data is not lost when you stop.

### View live logs

```bash
docker compose logs -f api       # API logs
docker compose logs -f qdrant    # database logs
```

### Restart the service

```bash
docker compose restart api
```

---

## For HR: How to Use

> This section is written for non-technical HR staff using the service through the ERP interface.

1. **Open the screening form** in your ERP system.
2. **Paste the full Job Description** into the text field.
3. **Set how many candidates** you want to see (default: 10).
4. **Click "Screen Resumes"** and wait 5–10 seconds.
5. **Review the results** — candidates are ranked from best fit to least fit, with a one-line reason for each.

Each result shows:
- **Candidate name**
- **Fit score** (0–100%, higher = better match)
- **Why they match** — one sentence from the AI explaining the fit
- **CV file path** — so you can find and open their actual CV

> 💡 **Tip:** The AI works best with detailed job descriptions. Include required skills, years of experience, location preferences, and any must-have qualifications.

---

## ERP Integration Guide

> This section is for the ERP development team implementing the API call.

### Authentication

Every request to the screening API (except `/health`) must include an API key in the request header:

```
X-API-Key: your-api-key-from-env-file
```

The API key is set in the `.env` file as `API_KEY`. The ERP team should obtain this value from whoever manages the server.

Missing or wrong key → `401 Unauthorized`

---

### API Reference

#### `POST /api/v1/screen` — Screen candidates

**Base URL:** `http://<server-ip>:8000`

**Headers:**
```
Content-Type: application/json
X-API-Key: <your-api-key>
```

**Request Body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `job_description` | string | ✅ Yes | — | Full text of the job description (min 20 chars) |
| `top_k` | integer | No | 10 | Number of candidates to return (1–50) |
| `filters` | object | No | `{}` | Optional filters (see below) |
| `filters.min_experience` | integer | No | null | Minimum years of experience |
| `filters.location` | string | No | null | Preferred location (matched by AI) |

**Example Request:**
```json
{
  "job_description": "We are hiring a Senior Backend Engineer with 5+ years of Python experience. The candidate should be proficient in FastAPI, PostgreSQL, and have exposure to microservices architecture. Prior experience in fintech or ERP systems is a plus. Location: Delhi NCR, hybrid work model.",
  "top_k": 10,
  "filters": {
    "min_experience": 5,
    "location": "Delhi"
  }
}
```

**Response Body:**

| Field | Type | Description |
|---|---|---|
| `job_id` | string (UUID) | Unique ID for this screening request |
| `screened_at` | string (ISO 8601) | Timestamp of when screening ran |
| `candidates` | array | Ranked list of candidates |
| `candidates[].candidate_id` | string | Unique candidate identifier |
| `candidates[].name` | string | Candidate name (extracted from CV) |
| `candidates[].score` | float (0.0–1.0) | Fit score (1.0 = perfect match) |
| `candidates[].match_reasoning` | string | One-sentence AI explanation |
| `candidates[].cv_path` | string | File path to the CV on the server |

**Example Response:**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "screened_at": "2024-01-15T10:30:00.123456+00:00",
  "candidates": [
    {
      "candidate_id": "3f7a2c1d-8b4e-5f6a-9c2d-1e0f4a8b7c6d",
      "name": "Rahul Sharma",
      "score": 0.94,
      "match_reasoning": "5+ years Python and FastAPI experience with prior fintech ERP integration background.",
      "cv_path": "/app/cvs/rahul_sharma.pdf"
    },
    {
      "candidate_id": "7c3e9f2a-1d5b-4e8c-a6f0-2b3c7d9e1f4a",
      "name": "Priya Mehta",
      "score": 0.88,
      "match_reasoning": "Strong PostgreSQL and microservices background; 6 years Python experience at scale.",
      "cv_path": "/app/cvs/priya_mehta.docx"
    }
  ]
}
```

---

#### `GET /health` — Service health check

No authentication required.

**Example Request:**
```
GET http://<server-ip>:8000/health
```

**Example Response (healthy):**
```json
{
  "status": "healthy",
  "qdrant_connected": true,
  "model_loaded": true,
  "version": "1.0.0"
}
```

**HTTP Status Codes:**
- `200` — Service is healthy
- `503` — Service is degraded (Qdrant or model issue)

> 💡 **Tip:** Call `/health` before displaying the screening form to show users whether the service is available.

---

#### Interactive API Documentation

The API ships with built-in interactive documentation at:

- **Swagger UI:** `http://<server-ip>:8000/docs`
- **ReDoc:** `http://<server-ip>:8000/redoc`

These pages let you test the API directly from your browser with no code required.

---

### Code Examples

#### cURL (terminal / shell scripts)

```bash
curl -X POST http://localhost:8000/api/v1/screen \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "job_description": "Looking for a Data Analyst with SQL, Python, and Power BI experience. Minimum 3 years in a corporate environment.",
    "top_k": 5
  }'
```

---

#### Python (requests)

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"

def screen_candidates(job_description: str, top_k: int = 10) -> dict:
    response = requests.post(
        f"{API_URL}/api/v1/screen",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        json={
            "job_description": job_description,
            "top_k": top_k,
        },
        timeout=30,  # seconds — LLM reranking takes 3–8s
    )
    response.raise_for_status()
    return response.json()


# Usage
result = screen_candidates(
    job_description="Senior Python Developer, FastAPI, 5+ years, Delhi",
    top_k=10,
)

for candidate in result["candidates"]:
    print(f"{candidate['name']:30} Score: {candidate['score']:.0%}")
    print(f"  → {candidate['match_reasoning']}")
    print()
```

---

#### JavaScript / Node.js (fetch)

```javascript
const API_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key-here';

async function screenCandidates(jobDescription, topK = 10) {
  const response = await fetch(`${API_URL}/api/v1/screen`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify({
      job_description: jobDescription,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Screening failed: ${error.detail}`);
  }

  return response.json();
}

// Usage
try {
  const result = await screenCandidates(
    'Senior Python Developer, FastAPI, 5+ years, Delhi',
    10,
  );

  result.candidates.forEach((c, i) => {
    console.log(`#${i + 1} ${c.name} — ${(c.score * 100).toFixed(0)}%`);
    console.log(`     ${c.match_reasoning}`);
  });
} catch (err) {
  console.error('Screening error:', err.message);
}
```

---

#### PHP (cURL)

```php
<?php

define('API_URL', 'http://localhost:8000');
define('API_KEY', 'your-api-key-here');

function screenCandidates(string $jobDescription, int $topK = 10): array {
    $payload = json_encode([
        'job_description' => $jobDescription,
        'top_k'           => $topK,
    ]);

    $ch = curl_init(API_URL . '/api/v1/screen');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 30,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'X-API-Key: ' . API_KEY,
        ],
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200) {
        throw new RuntimeException("Screening API error: HTTP $httpCode — $response");
    }

    return json_decode($response, true);
}

// Usage
try {
    $result = screenCandidates('Senior Python Developer, FastAPI, 5+ years, Delhi', 10);

    foreach ($result['candidates'] as $i => $candidate) {
        $score = number_format($candidate['score'] * 100, 0);
        echo "#" . ($i + 1) . " {$candidate['name']} — {$score}%\n";
        echo "     {$candidate['match_reasoning']}\n\n";
    }
} catch (RuntimeException $e) {
    error_log($e->getMessage());
}
```

---

#### C# / .NET (HttpClient)

```csharp
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

public class ResumeScreenerClient
{
    private readonly HttpClient _http;
    private const string BaseUrl = "http://localhost:8000";
    private const string ApiKey  = "your-api-key-here";

    public ResumeScreenerClient()
    {
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
        _http.DefaultRequestHeaders.Add("X-API-Key", ApiKey);
    }

    public async Task<ScreeningResponse> ScreenAsync(string jobDescription, int topK = 10)
    {
        var payload = new { job_description = jobDescription, top_k = topK };
        var content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json"
        );

        var response = await _http.PostAsync($"{BaseUrl}/api/v1/screen", content);
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<ScreeningResponse>(json)!;
    }
}

// Models
public record Candidate(string candidate_id, string name, float score,
                        string match_reasoning, string cv_path);
public record ScreeningResponse(string job_id, List<Candidate> candidates, string screened_at);
```

---

#### Java (HttpClient — Java 11+)

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class ResumeScreenerClient {

    private static final String BASE_URL = "http://localhost:8000";
    private static final String API_KEY  = "your-api-key-here";

    private final HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .build();

    public String screenCandidates(String jobDescription, int topK) throws Exception {
        String body = String.format(
            "{\"job_description\":\"%s\",\"top_k\":%d}",
            jobDescription.replace("\"", "\\\""), topK
        );

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + "/api/v1/screen"))
            .timeout(Duration.ofSeconds(30))
            .header("Content-Type", "application/json")
            .header("X-API-Key", API_KEY)
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build();

        HttpResponse<String> response = client.send(
            request, HttpResponse.BodyHandlers.ofString()
        );

        if (response.statusCode() != 200) {
            throw new RuntimeException("API error: " + response.statusCode() + " " + response.body());
        }
        return response.body(); // Parse with your preferred JSON library (Gson, Jackson, etc.)
    }
}
```

---

### Integration Patterns

#### Pattern 1: Inline Screening (Synchronous)

Call the API directly when the HR user clicks "Screen". Best for simple ERP setups.

```
User clicks "Screen"
      │
      ▼
ERP backend calls POST /api/v1/screen
      │  (awaits response, ~5–8 seconds)
      ▼
ERP renders candidate table to user
```

**Considerations:**
- Show a loading spinner while waiting (expected 5–8s)
- Set HTTP timeout to at least 30 seconds
- If the API returns 503, show "Service unavailable, try again in a moment"

---

#### Pattern 2: Async with Polling (Recommended for complex ERPs)

Submit screening in the background, poll for results. Better UX for enterprise systems.

```
User clicks "Screen"
      │
      ▼
ERP stores job_description in its DB → creates a ScreeningJob record
      │
      ▼
Background worker calls POST /api/v1/screen
      │
      ▼
Worker stores response in ScreeningJob.results
      │
      ▼
Frontend polls ERP endpoint every 2s until results are ready
```

This pattern lets the ERP track screening history and avoids browser timeout issues.

---

#### Pattern 3: Check Health Before Showing Form

```javascript
// On page load — only show the screening form if the service is up
async function checkServiceAvailability() {
  try {
    const res = await fetch('http://localhost:8000/health', { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}

const isAvailable = await checkServiceAvailability();
if (!isAvailable) {
  showBanner('Resume screening is temporarily unavailable. Contact IT.');
}
```

---

#### Pattern 4: Displaying CV Links

The `cv_path` field in the response is the **server-side file path**. To let HR open CVs, your ERP needs to either:

**Option A — Serve CVs directly from the ERP:**
Map the server path to a download URL in your ERP backend.

```python
# Example: Python/Django ERP view
CV_SERVER_BASE = "/app/cvs"       # server path prefix
CV_DOWNLOAD_BASE = "/hr/cv-files" # ERP URL prefix

def cv_url(cv_path: str) -> str:
    relative = cv_path.replace(CV_SERVER_BASE, "").lstrip("/")
    return f"{CV_DOWNLOAD_BASE}/{relative}"
```

**Option B — Use the cv_path as a network share path:**
If the CV folder is on a shared drive, the path may already be directly openable by HR workstations.

---

### Error Reference

| HTTP Status | Meaning | What to do |
|---|---|---|
| `200 OK` | Success | Parse and display results |
| `400 Bad Request` | Invalid request body | Check that `job_description` is at least 20 characters |
| `401 Unauthorized` | Missing or wrong API key | Verify the `X-API-Key` header matches the `API_KEY` in `.env` |
| `422 Unprocessable Entity` | Invalid field types | Check request body against the API reference above |
| `503 Service Unavailable` | Qdrant is down or not indexed | Check `/health` endpoint; may need to restart Qdrant or run indexer |
| Network timeout | Service not reachable | Check that Docker containers are running (`docker compose ps`) |

**Empty candidates array:** If the response contains `"candidates": []`, the CV collection has not been indexed yet. Run `docker compose run --rm indexer`.

---

## Configuration Reference

All configuration is in the `.env` file. Here is the full reference:

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_KEY` | ✅ Yes | — | Secret key for authenticating API requests |
| `GROQ_API_KEY` | ✅ Yes* | — | Groq API key (*if `LLM_PROVIDER=groq`) |
| `GEMINI_API_KEY` | ✅ Yes* | — | Gemini API key (*if `LLM_PROVIDER=gemini`) |
| `LLM_PROVIDER` | No | `groq` | LLM provider: `groq` or `gemini` |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model to use |
| `GEMINI_MODEL` | No | `gemini-1.5-flash` | Gemini model to use |
| `CV_FOLDER_PATH` | No | `./cvs` | Path to CV folder (supports relative and absolute paths) |
| `QDRANT_HOST` | No | `qdrant` | Qdrant hostname (use `qdrant` inside Docker, `localhost` outside) |
| `QDRANT_PORT` | No | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | No | `resumes` | Name of the Qdrant collection |
| `DEFAULT_TOP_K` | No | `10` | Default number of candidates to return |
| `RETRIEVAL_TOP_N` | No | `30` | Candidates fetched from vector DB before LLM reranking |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Embedding model name (**do not change** without re-indexing) |
| `API_PORT` | No | `8000` | Port the API is exposed on |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated); use `*` to allow all |

---

## Updating CVs

When you add, remove, or update CVs in your folder:

### Adding new CVs

1. Copy new `.pdf` or `.docx` files into the CV folder
2. Run: `docker compose run --rm indexer`
3. Only the new files are processed (unchanged files are skipped)

### Modifying an existing CV

1. Replace the file with the updated version
2. Run: `docker compose run --rm indexer`
3. The indexer detects the file has changed (MD5 hash differs) and re-indexes it

### Removing CVs

1. Delete the file from the folder
2. Run: `docker compose run --rm indexer`

> ⚠️ **Note:** The deleted file's vectors remain in Qdrant. They will still appear in results until you reset the database. To fully remove deleted CVs, reset the database and re-index:
> ```bash
> docker volume rm resume_screener_qdrant_data
> docker compose run --rm indexer
> ```

---

## Monitoring & Health

### Quick status check

```bash
# Check all containers are running and healthy
docker compose ps

# Check API is responding
curl http://localhost:8000/health

# Check how many CV chunks are in the database
curl http://localhost:6333/collections/resumes
```

### Viewing logs

```bash
# Live API logs
docker compose logs -f api

# Last 100 lines of indexer output from the last run
docker compose logs --tail=100 indexer

# Qdrant logs
docker compose logs -f qdrant
```

### Qdrant Web Dashboard

Qdrant includes a built-in web dashboard for inspecting the database:

```
http://localhost:6333/dashboard
```

Use this to see how many vectors are stored, run test queries, and monitor database health.

---

## Troubleshooting

### ❌ `docker compose ps` shows containers as unhealthy

```bash
# Check what's wrong
docker compose logs qdrant
docker compose logs api

# Restart
docker compose restart
```

### ❌ `/health` returns `"qdrant_connected": false`

Qdrant is not reachable from the API container.

```bash
# Check Qdrant is running
docker compose ps qdrant

# Restart Qdrant
docker compose restart qdrant

# Wait 15 seconds, then restart the API
docker compose restart api
```

### ❌ Screening returns `"candidates": []`

The database is empty. You need to index your CVs:

```bash
docker compose run --rm indexer
```

If the indexer ran but still empty, check that `CV_FOLDER_PATH` in `.env` points to the right directory and that it contains `.pdf` or `.docx` files.

### ❌ `401 Unauthorized` errors from ERP

The API key doesn't match. Check:
1. What `API_KEY` is set to in your `.env` file on the server
2. What the ERP is sending in the `X-API-Key` header
3. They must be exactly equal (case-sensitive, no extra spaces)

### ❌ Indexer runs but many files show `Failed`

```bash
# Run indexer with debug logging for more detail
docker compose run --rm -e LOG_LEVEL=DEBUG indexer
```

Common causes:
- **Scanned PDFs** (image-only, no text layer) — not supported, will be skipped with a warning
- **Password-protected PDFs** — not supported, will fail
- **Corrupted files** — will fail gracefully and be skipped

### ❌ `GROQ_API_KEY` errors / LLM reranking fails

The screening still works — it falls back to semantic similarity scores automatically. But to fix:

1. Check your key is correct: visit [console.groq.com](https://console.groq.com)
2. Check you haven't hit the free tier rate limit (14,400 req/day)
3. Check outbound internet is available from the server: `curl https://api.groq.com`

### ❌ Port 8000 is already in use

Change the port in `.env`:
```env
API_PORT=8080
```
Then restart: `docker compose down && docker compose up -d`

### ❌ `docker compose build` fails with network errors

The server may have blocked PyPI or Docker Hub. Check with IT that outbound connections to these domains are allowed:
- `registry-1.docker.io`
- `pypi.org`
- `files.pythonhosted.org`
- `download.pytorch.org`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                     │
│                                                             │
│  ┌─────────────────────────┐    ┌──────────────────────┐   │
│  │   FastAPI API (:8000)   │───▶│  Qdrant DB (:6333)   │   │
│  │                         │    │  (Named Volume)      │   │
│  │  • Auth middleware       │    │  384-dim cosine      │   │
│  │  • JD embedding (CPU)    │    │  vectors             │   │
│  │  • Vector retrieval      │    └──────────────────────┘   │
│  │  • LLM reranking        │                               │
│  └────────────┬────────────┘                               │
│               │                                             │
└───────────────┼─────────────────────────────────────────────┘
                │  (one HTTPS call per screen request)
                ▼
         Groq / Gemini API
```

**Indexer (run manually):**
```
cvs/ folder → parser.py (PDF/DOCX) → embedder.py (MiniLM) → Qdrant
                                         ↑
                               data/index_state.json
                               (tracks file hashes for skip logic)
```

**Embedding model:** `all-MiniLM-L6-v2` (90 MB, runs on CPU)
- Converts text to 384-dimensional vectors
- Same model used at index time and query time (required for correct similarity)

**LLM Reranker:** Groq (default) or Gemini Flash
- Called once per `/screen` request
- Receives job description + ~10 candidate summaries (not full CVs)
- Returns ranked list with scores and reasoning

---

## FAQ

**Q: Can I use this without a Groq/Gemini API key?**
Yes. If the LLM call fails (bad key, rate limit, no internet), the service automatically falls back to pure semantic similarity ranking. You lose the AI-written reasoning, but results are still returned.

**Q: How accurate is the screening?**
The semantic embedding step finds candidates whose CV text is semantically similar to the job description. The LLM reranking step refines this using role understanding. Results are significantly better than keyword matching but should always be reviewed by a human recruiter.

**Q: What CV formats are supported?**
`.pdf` and `.docx`. Note: scanned PDFs (image-only, no text layer) cannot be processed and will be skipped. Word documents created by any version of Microsoft Word or LibreOffice work.

**Q: Is candidate data sent to the AI provider?**
Only short text excerpts (~800 words) from the top ~10 candidates are sent per request. Full CVs are never transmitted. No data is stored on the AI provider's side beyond their standard API request logging.

**Q: Can multiple users use this simultaneously?**
Yes, but with some caveats. The API handles concurrent requests, but the embedding model is loaded once and CPU-only, so very high concurrency (10+ simultaneous screens) may cause slowdowns. For a 3-person HR team, this is not a concern.

**Q: How do I back up the CV database?**
Back up the Docker volume `resume_screener_qdrant_data`. Alternatively, simply keep your `cvs/` folder and `data/index_state.json` backed up — you can always rebuild the Qdrant database by running the indexer again.

**Q: The server was restarted. Do I need to re-index?**
No. Qdrant data is in a persistent Docker named volume and survives server reboots. Run `docker compose up -d` after restart and the service is ready immediately.

**Q: Can I change the AI provider later?**
Yes. Change `LLM_PROVIDER` in `.env` from `groq` to `gemini` (and set `GEMINI_API_KEY`), then restart: `docker compose restart api`. No re-indexing needed.

**Q: How do I add support for more CV file types?**
The parser module (`indexer/parser.py`) can be extended. Open a request with the developer.
