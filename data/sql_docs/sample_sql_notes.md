# SQL Complete Reference Guide

## SELECT Statement

The SELECT statement retrieves data from one or more tables.

```sql
SELECT column1, column2 FROM table_name WHERE condition;
SELECT * FROM employees WHERE department = 'Engineering';
SELECT name, salary FROM employees ORDER BY salary DESC LIMIT 10;
```

## WHERE Clause

Filter rows using conditions:

```sql
SELECT * FROM orders WHERE status = 'completed' AND total > 100;
SELECT * FROM users WHERE created_at >= '2024-01-01';
SELECT * FROM products WHERE price BETWEEN 10 AND 100;
SELECT * FROM customers WHERE city IN ('Chennai', 'Mumbai', 'Delhi');
SELECT * FROM users WHERE name LIKE '%john%';
```

## JOINs

### INNER JOIN
Returns rows that have matching values in both tables.

```sql
SELECT e.name, d.department_name
FROM employees e
INNER JOIN departments d ON e.department_id = d.id;
```

### LEFT JOIN
Returns all rows from the left table, and matched rows from the right.

```sql
SELECT c.name, o.order_id
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id;
-- Customers with no orders will show NULL for order_id
```

### RIGHT JOIN
Returns all rows from the right table, matched rows from the left.

```sql
SELECT e.name, d.department_name
FROM employees e
RIGHT JOIN departments d ON e.department_id = d.id;
```

### FULL OUTER JOIN
Returns all rows when there is a match in either table.

```sql
SELECT c.name, o.order_id
FROM customers c
FULL OUTER JOIN orders o ON c.id = o.customer_id;
```

### SELF JOIN
Joining a table with itself.

```sql
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

### CROSS JOIN
Returns the Cartesian product of two tables.

```sql
SELECT colors.name, sizes.name FROM colors CROSS JOIN sizes;
```

## GROUP BY and HAVING

```sql
-- Count orders per customer
SELECT customer_id, COUNT(*) AS order_count
FROM orders
GROUP BY customer_id;

-- Filter groups with HAVING
SELECT customer_id, COUNT(*) AS order_count
FROM orders
GROUP BY customer_id
HAVING COUNT(*) > 5;

-- Multiple aggregations
SELECT department, AVG(salary), MAX(salary), MIN(salary), COUNT(*)
FROM employees
GROUP BY department
ORDER BY AVG(salary) DESC;
```

## Aggregate Functions

```sql
COUNT(*) -- count all rows
COUNT(DISTINCT column) -- count unique values
SUM(column) -- total sum
AVG(column) -- average
MAX(column) -- maximum value
MIN(column) -- minimum value
```

## Subqueries

### Scalar Subquery
```sql
SELECT name, salary,
  (SELECT AVG(salary) FROM employees) AS company_avg
FROM employees;
```

### IN Subquery
```sql
SELECT name FROM employees
WHERE department_id IN (
  SELECT id FROM departments WHERE location = 'Chennai'
);
```

### EXISTS Subquery
```sql
SELECT c.name FROM customers c
WHERE EXISTS (
  SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

### Correlated Subquery
```sql
SELECT name, salary FROM employees e
WHERE salary > (
  SELECT AVG(salary) FROM employees
  WHERE department_id = e.department_id
);
```

## CTEs (Common Table Expressions)

```sql
-- Simple CTE
WITH high_earners AS (
  SELECT name, salary FROM employees WHERE salary > 80000
)
SELECT * FROM high_earners ORDER BY salary DESC;

-- Multiple CTEs
WITH
dept_totals AS (
  SELECT department_id, SUM(salary) AS total_salary
  FROM employees GROUP BY department_id
),
dept_avg AS (
  SELECT department_id, AVG(salary) AS avg_salary
  FROM employees GROUP BY department_id
)
SELECT d.department_name, dt.total_salary, da.avg_salary
FROM departments d
JOIN dept_totals dt ON d.id = dt.department_id
JOIN dept_avg da ON d.id = da.department_id;

-- Recursive CTE (hierarchy)
WITH RECURSIVE org_chart AS (
  SELECT id, name, manager_id, 1 AS level
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, e.manager_id, oc.level + 1
  FROM employees e
  JOIN org_chart oc ON e.manager_id = oc.id
)
SELECT * FROM org_chart ORDER BY level;
```

## Window Functions

```sql
-- ROW_NUMBER
SELECT name, salary,
  ROW_NUMBER() OVER (ORDER BY salary DESC) AS rank
FROM employees;

-- RANK and DENSE_RANK
SELECT name, salary,
  RANK() OVER (ORDER BY salary DESC) AS rank,
  DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank
FROM employees;

-- PARTITION BY
SELECT name, department, salary,
  ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank
FROM employees;

-- LAG and LEAD
SELECT month, revenue,
  LAG(revenue, 1) OVER (ORDER BY month) AS prev_month,
  revenue - LAG(revenue, 1) OVER (ORDER BY month) AS growth
FROM monthly_revenue;

-- Running Total
SELECT order_date, amount,
  SUM(amount) OVER (ORDER BY order_date) AS running_total
FROM orders;

-- Moving Average
SELECT date, sales,
  AVG(sales) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d
FROM daily_sales;
```

## SQL Indexes

Indexes speed up data retrieval at the cost of extra storage and slower writes.

```sql
-- Create index
CREATE INDEX idx_email ON users(email);

-- Unique index
CREATE UNIQUE INDEX idx_unique_email ON users(email);

-- Composite index
CREATE INDEX idx_name_dept ON employees(last_name, department_id);

-- Drop index
DROP INDEX idx_email;

-- When to use indexes:
-- Columns used in WHERE clauses
-- Columns used in JOIN conditions
-- Columns used in ORDER BY
-- Columns with high cardinality (many unique values)
```

## Finding Duplicates

```sql
-- Find duplicate emails
SELECT email, COUNT(*) AS count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Find all rows with duplicate email
SELECT * FROM users
WHERE email IN (
  SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1
)
ORDER BY email;

-- Delete duplicates keeping the first one
DELETE FROM users WHERE id NOT IN (
  SELECT MIN(id) FROM users GROUP BY email
);
```

## Database Normalization

### 1NF (First Normal Form)
- Each column contains atomic values
- No repeating groups

### 2NF (Second Normal Form)
- Must be in 1NF
- All non-key attributes fully depend on the primary key

### 3NF (Third Normal Form)
- Must be in 2NF
- No transitive dependencies (non-key column depends on another non-key column)

### BCNF (Boyce-Codd Normal Form)
- Every determinant must be a candidate key

## Query Optimization Tips

1. **Use indexes on filtered columns**: `WHERE department_id = 5` benefits from an index on department_id
2. **Avoid SELECT ***: Only select columns you need
3. **Use EXISTS instead of IN for large subqueries**: EXISTS stops at first match
4. **Avoid functions on indexed columns in WHERE**: `WHERE YEAR(created_at) = 2024` prevents index use; use `WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'` instead
5. **Use LIMIT** to restrict result sets
6. **Analyze query execution plans**: Use EXPLAIN to see how the query runs
7. **Avoid wildcard at start of LIKE**: `LIKE '%john'` can't use an index; `LIKE 'john%'` can

## SQL Dialects: MySQL vs PostgreSQL vs SQLite

| Feature | MySQL | PostgreSQL | SQLite |
|---|---|---|---|
| FULL OUTER JOIN | Not native | Yes | Not native |
| Window Functions | 8.0+ | Yes | 3.25+ |
| JSON Support | Yes | Full JSONB | Basic |
| CTEs | 8.0+ | Yes | 3.35+ |
| UPSERT | ON DUPLICATE KEY | ON CONFLICT | ON CONFLICT |

## Common SQL Interview Questions

### Top N per group
```sql
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rn
  FROM employees
) t WHERE rn <= 3;
```

### Second highest salary
```sql
SELECT MAX(salary) FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);
```

### Cumulative percentage
```sql
SELECT category, sales,
  ROUND(100.0 * SUM(sales) OVER (ORDER BY sales DESC) / SUM(sales) OVER (), 2) AS cumulative_pct
FROM category_sales;
```

### Pivot table
```sql
SELECT
  student,
  SUM(CASE WHEN subject = 'Math' THEN score END) AS math,
  SUM(CASE WHEN subject = 'Science' THEN score END) AS science,
  SUM(CASE WHEN subject = 'English' THEN score END) AS english
FROM scores
GROUP BY student;
```

## CASE WHEN

```sql
SELECT name, salary,
  CASE
    WHEN salary >= 100000 THEN 'Senior'
    WHEN salary >= 60000 THEN 'Mid-level'
    ELSE 'Junior'
  END AS level
FROM employees;
```

## String Functions

```sql
UPPER(name), LOWER(name)
LENGTH(name)
SUBSTRING(name, 1, 3)  -- first 3 chars
TRIM(name)             -- remove whitespace
REPLACE(name, 'old', 'new')
CONCAT(first_name, ' ', last_name)
COALESCE(value, 'default')  -- return first non-null
```

## Date Functions

```sql
-- Current date/time
NOW(), CURRENT_TIMESTAMP, CURRENT_DATE

-- Extract parts
YEAR(date), MONTH(date), DAY(date)
DATE_FORMAT(date, '%Y-%m') -- MySQL
TO_CHAR(date, 'YYYY-MM')  -- PostgreSQL

-- Date arithmetic
DATE_ADD(date, INTERVAL 7 DAY)  -- MySQL
date + INTERVAL '7 days'        -- PostgreSQL

-- Difference
DATEDIFF(end_date, start_date)
```
