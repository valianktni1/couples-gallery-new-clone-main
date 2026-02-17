# TrueNAS Deployment Guide

This guide explains how to deploy the optimized Couples Gallery application on TrueNAS Scale using Docker Compose.

## Prerequisites

- TrueNAS Scale installed and running.
- Access to "Custom App" or "Launch Docker Image" feature (or Portainer if installed).
- A dataset created for persistent storage (e.g., `/mnt/tank/apps/gallery`).

## Preparation

1.  **Clone or Copy Repo**: Ensure this repository is accessible on your TrueNAS server, or you can copy the contents of `truenas_docker_compose.yml` to use directly in the TrueNAS UI.
2.  **Create Folders**: Create the following folders in your dataset to persist data:
    -   `db` (for MongoDB data)
    -   `thumbnails` (generated thumbnails)
    -   `previews` (generated previews)
    -   `files` (your original high-res images)

## Deployment Steps

1.  **Compose File**: Use the `truenas_docker_compose.yml` file. It is pre-configured with your specific paths.
2.  **Verify Paths**:
    -   App Data: `/mnt/apps/newweddingsbymarkgallery` (contains `db`, `thumbnails`, `previews`)
    -   User Files: `/mnt/nextcloud/newwedidngsbymarkuserfiles` (contains original full-res images/videos)
3.  **Environment Variables**:
    -   Update `JWT_SECRET` in the `backend` service to a secure random string.
4.  **Port Mapping**:
    -   The application is exposed on port **3037**.

## Verify Deployment

1.  Open `http://<truenas-ip>:3037` in your browser.
2.  You should see the gallery application.
3.  Go to `/setup` if you need to create an initial admin account (or check API documentation).

## Features

-   **Optimized Performance**: Uses GZip, WebP images, and virtual scrolling.
-   **Pagination**: Handles large galleries efficiently.
-   **TrueNAS Ready**: Configured for persistent storage and containerized deployment.
