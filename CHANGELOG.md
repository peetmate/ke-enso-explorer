# Changelog

---

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

---

## NDMA data edition — 2026-11-24

- Port the validated national and county bulletin index from source commit `ea9e5d9`, including document metadata, two-order closure evidence, cache replay and maintained NDMA parsing/sidecar generation. This source branch previously held 107 national records; it now holds 3,539 national and county records. Notebook software version is unchanged because this isolated port does not change its UI or loaders.
