import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar, Container, Nav } from 'react-bootstrap';

// Import your two isolated screens
import UserRegistration from './UserRegistration'; 
import AdminLiveMonitor from './AdminLiveMonitor'; 

export default function App() {
  return (
    <BrowserRouter>
      {/* 1. Top Navigation Bar */}
      <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand>Smart Station</Navbar.Brand>
          <Nav className="me-auto">
            <Nav.Link href="/register">Customer Portal</Nav.Link>
            <Nav.Link href="/admin">Command Center</Nav.Link>
          </Nav>
        </Container>
      </Navbar>

      {/* 2. Strict Page Routing */}
      <Routes>
        {/* PATH 1: The isolated User Registration page */}
        <Route path="/register" element={<UserRegistration />} />

        {/* PATH 2: The isolated Admin Dashboard (Camera + Logs + DB Modal) */}
        <Route path="/admin" element={<AdminLiveMonitor />} />

        {/* Fallback: Automatically redirect the root URL to the registration page */}
        <Route path="/" element={<Navigate to="/register" replace />} />
      </Routes>
    </BrowserRouter>
  );
}