"""
Calibration Verification Script for Jan Document Plugin

Tests PDF extraction by uploading the calibration PDF and asking
questions with known answers. Provides clear pass/fail feedback.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Import calibration data
from create_calibration_pdf import get_verification_data, create_calibration_pdf

# Configuration
PROXY_URL = os.getenv("PROXY_URL", "http://localhost:1338")
TIMEOUT = 30


class CalibrationVerifier:
    def __init__(self, proxy_url=PROXY_URL):
        self.proxy_url = proxy_url.rstrip("/")
        self.calibration_data = get_verification_data()
        self.results = []

    def log(self, message, level="INFO"):
        """Print formatted log message."""
        prefix = {
            "INFO": "[INFO]",
            "OK": "[PASS]",
            "FAIL": "[FAIL]",
            "WARN": "[WARN]",
            "DEBUG": "[DEBUG]"
        }.get(level, "[INFO]")
        print(f"{prefix} {message}")

    def check_server(self):
        """Check if the proxy server is running."""
        self.log("Checking if Jan Document Plugin server is running...")
        try:
            response = requests.get(f"{self.proxy_url}/health", timeout=5)
            if response.status_code == 200:
                self.log("Server is running!", "OK")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            self.log(f"Connection error: {e}", "WARN")

        self.log("Server not running. Please start it first.", "FAIL")
        self.log("Run: python jan_proxy.py")
        return False

    def upload_calibration_pdf(self):
        """Upload the calibration PDF to the server."""
        pdf_path = Path(__file__).parent / "JanDocPlugin_Calibration.pdf"

        # Create PDF if it doesn't exist
        if not pdf_path.exists():
            self.log("Calibration PDF not found, generating...")
            create_calibration_pdf(str(pdf_path))

        self.log(f"Uploading calibration PDF: {pdf_path.name}")

        try:
            with open(pdf_path, "rb") as f:
                files = {"file": (pdf_path.name, f, "application/pdf")}
                response = requests.post(
                    f"{self.proxy_url}/documents",
                    files=files,
                    timeout=TIMEOUT
                )

            if response.status_code == 200:
                data = response.json()
                self.log(f"PDF uploaded successfully!", "OK")
                self.log(f"  - Document ID: {data.get('document_id', 'N/A')}")
                self.log(f"  - Chunks created: {data.get('chunks', 'N/A')}")
                return True
            else:
                self.log(f"Upload failed: {response.status_code}", "FAIL")
                self.log(f"  Response: {response.text}")
                return False

        except Exception as e:
            self.log(f"Upload error: {e}", "FAIL")
            return False

    def ask_question(self, question):
        """Ask a question to the LLM via the proxy."""
        try:
            payload = {
                "model": "gpt-3.5-turbo",  # Will be proxied to Jan's model
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "temperature": 0.1,  # Low temp for consistent answers
                "max_tokens": 200
            }

            response = requests.post(
                f"{self.proxy_url}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                return answer.strip()
            else:
                return None

        except Exception as e:
            self.log(f"Query error: {e}", "WARN")
            return None

    def verify_extraction(self):
        """Run verification tests using Q&A pairs."""
        self.log("\n" + "=" * 60)
        self.log("Starting Extraction Verification Tests")
        self.log("=" * 60 + "\n")

        qa_pairs = self.calibration_data["qa_pairs"]
        passed = 0
        failed = 0

        for i, (question, expected) in enumerate(qa_pairs, 1):
            self.log(f"\nTest {i}/{len(qa_pairs)}: {question}")

            answer = self.ask_question(question)

            if answer is None:
                self.log("No response received", "FAIL")
                failed += 1
                self.results.append({
                    "question": question,
                    "expected": expected,
                    "actual": None,
                    "passed": False
                })
                continue

            # Check if expected value is in the answer
            if expected.lower() in answer.lower():
                self.log(f"Expected '{expected}' - Found in response", "OK")
                passed += 1
                self.results.append({
                    "question": question,
                    "expected": expected,
                    "actual": answer,
                    "passed": True
                })
            else:
                self.log(f"Expected '{expected}'", "FAIL")
                self.log(f"Got: {answer[:100]}...")
                failed += 1
                self.results.append({
                    "question": question,
                    "expected": expected,
                    "actual": answer,
                    "passed": False
                })

            # Small delay between requests
            time.sleep(1)

        return passed, failed

    def print_summary(self, passed, failed):
        """Print test summary."""
        total = passed + failed

        self.log("\n" + "=" * 60)
        self.log("VERIFICATION SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")

        if failed == 0:
            self.log("\n" + "*" * 60)
            self.log("ALL TESTS PASSED - PDF EXTRACTION IS WORKING!", "OK")
            self.log("*" * 60)
            return True
        else:
            self.log(f"\n{failed} test(s) failed. Check the output above.", "WARN")
            self.log("\nPossible issues:")
            self.log("  1. PDF was not properly extracted")
            self.log("  2. LLM is not using document context")
            self.log("  3. Embedding/retrieval not finding relevant chunks")
            return False

    def run_full_verification(self):
        """Run complete verification process."""
        print("\n" + "=" * 60)
        print("Jan Document Plugin - Calibration Verification")
        print("=" * 60 + "\n")

        # Step 1: Check server
        if not self.check_server():
            return False

        # Step 2: Upload calibration PDF
        self.log("\n--- Step 2: Upload Calibration PDF ---")
        if not self.upload_calibration_pdf():
            return False

        # Give time for indexing
        self.log("\nWaiting for document indexing...")
        time.sleep(2)

        # Step 3: Run verification tests
        self.log("\n--- Step 3: Run Verification Tests ---")
        passed, failed = self.verify_extraction()

        # Step 4: Print summary
        return self.print_summary(passed, failed)


def main():
    """Main entry point."""
    verifier = CalibrationVerifier()
    success = verifier.run_full_verification()

    # Save results to file
    results_file = Path(__file__).parent / "verification_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success": success,
            "tests": verifier.results
        }, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
