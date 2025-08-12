import os
import httpx
import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from dataclasses import dataclass


@dataclass
class FourGeeksCredentials:
    username: str
    password: str


class FourGeeksClient:
    BASE_URL = "https://breathecode.herokuapp.com/v1"

    def __init__(self, credentials: FourGeeksCredentials):
        self.credentials = credentials
        self._token: Optional[str] = None
        self._client = httpx.Client()

    def _get_headers(self, academy_id: int = 6) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Academy": str(academy_id),
        }
        if self._token:
            headers["Authorization"] = f"Token {self._token}"
        return headers

    def login(self) -> None:
        """Authenticate with 4Geeks API and get token"""
        try:
            response = self._client.post(
                f"{self.BASE_URL}/auth/login/",
                json={
                    "email": self.credentials.username,
                    "password": self.credentials.password
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            self._token = response.json()["token"]
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error occurred in FourGeeksClient login: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in FourGeeksClient login: {e}")
        except Exception as e:
            logging.error(f"Error occurred in FourGeeksClient login: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in FourGeeksClient login: {e}")

    def get_member_by_email(self, email: str, roles: List[str] = ["student"], academy_id: Optional[int] = 6) -> Dict[str, Any]:
        """Get student information by email"""
        if not self._token:
            self.login()

        try:
            response = self._client.get(
                f"{self.BASE_URL}/auth/academy/member/{email}",
                params={"roles": ",".join(roles)},
                headers=self._get_headers(academy_id=academy_id)
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                logging.error(
                    f"Email not found")
                raise HTTPException(
                    status_code=status_code, detail=f"Email not found")
            else:
                logging.error(
                    f"HTTP error in trying to get_member_by_email: {e}")
                raise HTTPException(
                    status_code=status_code, detail=f"HTTP error in trying to get_member_by_email: {e.response.text}")
        except Exception as e:
            logging.error(
                f"Error in trying to get_member_by_email: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error in trying to get_member_by_email: {e}")

    def get_cohort(self, cohort_id: int) -> Dict[str, Any]:
        """Get cohort information by ID"""
        if not self._token:
            self.login()

        try:
            response = self._client.get(
                f"{self.BASE_URL}/admissions/cohort/{cohort_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in FourGeeksClient get_cohort: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in FourGeeksClient get_cohort: {e}")
        except Exception as e:
            logging.error(f"Error occurred in FourGeeksClient get_cohort: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in FourGeeksClient get_cohort: {e}")

    def get_cohort_user(self, cohort_id: int, user_id: int) -> Dict[str, Any]:
        """Get cohort user information"""
        if not self._token:
            self.login()

        try:
            response = self._client.get(
                f"{self.BASE_URL}/admissions/cohort/{cohort_id}/user/{user_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in FourGeeksClient get_cohort_user: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in FourGeeksClient get_cohort_user: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in FourGeeksClient get_cohort_user: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in FourGeeksClient get_cohort_user: {e}")

    def get_user_enrollments(self, user_id: int, params: Optional[Dict[str, Any]] = {}, academy_id: Optional[int] = 6) -> List[Dict[str, Any]]:
        """Get all cohorts for a specific user"""
        if not self._token:
            self.login()

        try:
            response = self._client.get(
                f"{self.BASE_URL}/admissions/academy/cohort/user",
                params={"users": user_id, **params},
                headers=self._get_headers(academy_id=academy_id)
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in FourGeeksClient get_user_cohorts: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in FourGeeksClient get_user_cohorts: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in FourGeeksClient get_user_cohorts: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in FourGeeksClient get_user_cohorts: {e}")

    def __del__(self):
        """Close the httpx client when the object is destroyed"""
        if hasattr(self, '_client') and self._client:
            self._client.close()
