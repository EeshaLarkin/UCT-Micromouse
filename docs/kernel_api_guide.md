# Micromouse Kernel & API Developer Guide

This document explains the three-tier software architecture of the UCT Micromouse, detailing the low-level C Kernel (Tier 1), the network telemetry protocol with delta and sparse encoding, and the high-level Python API (Tier 2-3) used by students for simulation and hardware control.

---

## 1. The Three-Tier Architecture

The software stack is organized into three distinct layers to decouple physical hardware interfaces from high-level solving intelligence:


