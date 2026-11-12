import React, { useState } from 'react';
import { Form, Button, Container, Card, Alert, Badge } from 'react-bootstrap';
import axios from 'axios';

export default function UserRegistration() {
  const [formData, setFormData] = useState({ plate_number: '', vehicle_type: 'Car', is_paid: false });
  const [ticketData, setTicketData] = useState(null);
  const [message, setMessage] = useState(null);

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await axios.post('http://127.0.0.1:8080/register-vehicle', formData);
      setMessage({ type: 'success', text: 'Vehicle registered! Loading ticket...' });
      fetchMyTicket(formData.plate_number);
    } catch (error) {
      setMessage({ type: 'danger', text: 'Registration failed.' });
    }
  };

  const fetchMyTicket = async (plate) => {
    try {
      const response = await axios.get(`http://127.0.0.1:8080/my-ticket/${plate}`);
      if (response.data.status === 'success') {
        setTicketData(response.data);
      } else {
        setMessage({ type: 'danger', text: response.data.message || 'Ticket not found.' });
        setTicketData(null);
      }
    } catch (error) {
      console.error("Ticket fetch error:", error);
      setMessage({ type: 'danger', text: 'Failed to connect to backend.' });
      setTicketData(null);
    }
  };

  const handlePayment = async () => {
    try {
      await axios.put(`http://127.0.0.1:8080/complete-payment/${ticketData.booking.plate_number}`);
      setMessage({ type: 'success', text: 'Payment processed successfully!' });
      fetchMyTicket(ticketData.booking.plate_number);
    } catch (error) {
      setMessage({ type: 'danger', text: 'Payment simulation failed.' });
    }
  };

  const handleStartFueling = async () => {
    try {
      const response = await axios.post(`http://127.0.0.1:8080/trigger-fueling/${ticketData.booking.plate_number}`);
      if (response.data.status === 'success') {
        setMessage({ type: 'success', text: 'Pump activated! Fueling in progress...' });
      } else {
        setMessage({ type: 'danger', text: response.data.message });
      }
      fetchMyTicket(ticketData.booking.plate_number);
    } catch (error) {
      setMessage({ type: 'danger', text: 'Failed to communicate with Master Orchestrator.' });
    }
  };

  const handleDelete = async () => {
    // Reset the frontend state to go back to the registration screen
    setTicketData(null);
    setMessage(null);
    setFormData({ plate_number: '', vehicle_type: 'Car', is_paid: false });
  };

  // ==========================================
  // VIEW 1: THE DIGITAL TICKET
  // ==========================================
  if (ticketData) {
    return (
      <Container className="mt-5" style={{ maxWidth: '500px' }}>
        <Card className="shadow-sm">
          <Card.Header className="bg-dark text-white text-center">
            <h4>Digital Ticket</h4>
          </Card.Header>
          <Card.Body>
            {message && <Alert variant={message.type}>{message.text}</Alert>}
            
            <h2 className="mb-3">{ticketData?.booking?.plate_number}</h2>
            {/* Checks for both spellings of vehicle_type from the database */}
            <p className="text-muted mb-1">Type: {ticketData?.booking?.vehichle_type || ticketData?.booking?.vehicle_type}</p>
            
            <p className="mb-3">
              Payment: <Badge bg={ticketData?.booking?.is_paid ? 'success' : 'warning'}>
                {ticketData?.booking?.is_paid ? 'Completed' : 'Pending'}
              </Badge>
            </p>
            
            <div className="mb-4">
              <h5>Station AI Status</h5>
              <Badge bg={ticketData?.result?.decision === 'APPROVED' ? 'success' : 
                         ticketData?.result?.decision === 'REJECTED' ? 'danger' : 'warning'} className="fs-6 p-2">
                {ticketData?.result?.decision}
              </Badge>
              <p className="mt-2 text-muted small">{ticketData?.result?.reason}</p>
            </div>

            {ticketData?.booking && !ticketData.booking.is_paid && (
              <Button variant="success" onClick={handlePayment} className="w-100 mb-2">
                Simulate Payment
              </Button>
            )}

            {ticketData?.booking?.is_paid ? (
              <Button variant="primary" size="lg" onClick={handleStartFueling} className="w-100 mb-3 fw-bold shadow-sm">
                Start Fueling (Trigger ESP32)
              </Button>
            ) : null}

            <Button variant="outline-danger" onClick={handleDelete} className="w-100 mb-2">
              Cancel Registration
            </Button>
            
            <Button variant="secondary" onClick={() => {
              setTicketData(null);
              setMessage(null);
            }} className="w-100">
              Back to Home
            </Button>
          </Card.Body>
        </Card>
      </Container>
    );
  }

  // ==========================================
  // VIEW 2: THE REGISTRATION FORM
  // ==========================================
  return (
    <Container className="mt-5" style={{ maxWidth: '500px' }}>
      <Card className="shadow-sm">
        <Card.Header className="bg-primary text-white text-center">
          <h4>Register Vehicle</h4>
        </Card.Header>
        <Card.Body>
          {message && <Alert variant={message.type}>{message.text}</Alert>}
          
          <Form onSubmit={handleRegister}>
            <Form.Group className="mb-3">
              <Form.Label>License Plate Number</Form.Label>
              <Form.Control 
                type="text" 
                placeholder="e.g. KL 10 AB 1234" 
                value={formData.plate_number}
                onChange={(e) => setFormData({...formData, plate_number: e.target.value})}
                required 
              />
            </Form.Group>

            <Form.Group className="mb-4">
              <Form.Label>Vehicle Type</Form.Label>
              <Form.Select 
                value={formData.vehicle_type}
                onChange={(e) => setFormData({...formData, vehicle_type: e.target.value})}
              >
                <option value="Car">Car</option>
                <option value="Truck">Truck</option>
                <option value="Bike">Bike</option>
              </Form.Select>
            </Form.Group>

            <Button variant="primary" type="submit" className="w-100 fw-bold">
              Complete Registration
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </Container>
  );
}