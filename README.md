# MovieLens Data Analysis Project
## Project Overview
This project is a comprehensive analysis of the MovieLens dataset, which includes information about movies, ratings, tags, and links to external databases. The implementation consists of several Python classes that process and analyze different aspects of the dataset, providing insights into movie trends, user behavior, and content characteristics.

## Key Features
### **1. Data Processing Classes**
**Movies:** Analyzes movie data including genres, release years, and movie titles

**Ratings:** Processes user ratings with methods for analyzing distribution by year, rating values, and user behavior

**Tags:** Handles user-generated tags with functionality for analyzing tag popularity, length, and content

**Links:** Manages external database links (IMDb, TMDb) and fetches additional movie details

### **2. Analytical Capabilities**
- Statistical analysis of movie ratings (average, median, variance)
- Top-N rankings by various metrics (directors, budgets, profitability)
- Genre and release year distributions
- Tag analysis (most popular, longest, most words)
- User rating patterns and controversial opinions

### **3. Performance Optimization**
- Efficient data loading and processing
- Caching mechanisms for external data fetching
- Comprehensive error handling

### **4. Testing**
- pytest test suite covering all major functionality
- Sample data fixtures for reliable testing

## What You Did in This Project
### **Data Processing:**

- Implemented robust CSV parsing with proper handling of quoted fields and special characters

- Created efficient data structures for storing and accessing movie information

- Developed methods for cleaning and normalizing data

### **Web Scraping:**

- Built functionality to fetch additional movie details from IMDb

- Implemented proper request headers and error handling for web requests

- Created parsers for extracting specific fields from IMDb pages

### **Statistical Analysis:**

- Calculated various statistical measures (averages, medians, variances)

- Implemented ranking systems for movies, directors, and users

- Developed methods for analyzing distributions (genres, release years, ratings)

### **Data Visualization (through analysis):**

- Although not graphical, created methods that generate insightful textual representations of data trends

- Implemented sorting and filtering to highlight key patterns in the data

### **Performance Optimization:**

- Added caching for expensive operations (like web requests)

- Optimized data structures for efficient lookups

- Implemented batch processing where appropriate

### **Testing:**

- Created a comprehensive test suite

- Used fixtures for test data

- Verified edge cases and error conditions

## How to Use
- Clone the repository
- Install dependencies via requirements
- Place MovieLens data files in the data-folder directory
- Run tests with pytest
- Import and use the classes in your Python code

## Data Sources
The project works with the standard MovieLens dataset files:

- movies.csv
- ratings.csv
- tags.csv
- links.csv

## Dependencies
Dependencies are in requirements.txt
