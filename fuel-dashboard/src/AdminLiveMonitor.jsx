import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Table, Badge, Button, Modal, Spinner } from 'react-bootstrap';
import axios from 'axios';



export default function AdminLiveMonitor() {
  const [registrations, setRegistrations] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  
  // NEW: State for real-time camera extraction
  const [liveStatus, setLiveStatus] = useState({ plate: null, message: "Waiting for vehicle..." });

  useEffect(() => {
    fetchData();
    // Poll database logs every 3 seconds
    const dataInterval = setInterval(fetchData, 3000);
    // Poll live Vision Agent status every 1 second
    const statusInterval = setInterval(fetchLiveStatus, 1000);
    
    return () => {
      clearInterval(dataInterval);
      clearInterval(statusInterval);
    };
  }, []);

  const fetchData = async () => {
    try {
      const regResponse = await axios.get('http://127.0.0.1:8080/all-registrations');
      setRegistrations(regResponse.data.data || []);
      
      const logResponse = await axios.get('http://127.0.0.1:8080/audit-logs');
      setAuditLogs(logResponse.data.data || []);
    } catch (error) {
      console.error("Backend fetch failed:", error);
    }
  };

  const fetchLiveStatus = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8080/live-status');
      if (response.data) setLiveStatus(response.data);
    } catch (error) {
      // Fails silently if Vision Agent isn't broadcasting yet
    }
  };

  return (
    <Container fluid className="px-4 mt-4">
      <Row>
        {/* ========================================== */}
        {/* LEFT COLUMN: LIVE ANPR CAMERA WITH OVERLAY */}
        {/* ========================================== */}
        <Col lg={7} className="mb-4">
          <Card className="shadow-sm border-0 bg-dark h-100">
            <Card.Header className="text-white border-secondary d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Live ANPR Camera Feed</h5>
            </Card.Header>
            <Card.Body className="p-0 position-relative d-flex align-items-center justify-content-center" style={{ minHeight: '600px', backgroundColor: '#1a1a1a', overflow: 'hidden' }}>
              
              {/* Live YOLO Video Stream */}
              <img 
                src="http://127.0.0.1:8080/video-feed" 
                alt="Live Camera Feed Offline" 
                style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
                onError={(e) => { e.target.style.display = 'none'; }} // Hides broken image if Python isn't streaming yet
              />
              
              {/* FLOATING TARGET OVERLAY: Only shows when a plate is detected */}
              {liveStatus.plate && (
                <div className="position-absolute top-50 start-50 translate-middle w-75 p-4 rounded shadow-lg" 
                     style={{ backgroundColor: 'rgba(0, 0, 0, 0.85)', border: '2px solid #0d6efd', zIndex: 10 }}>
                  <h3 className="text-white mb-3 text-center">
                    Target Acquired: <span className="text-info font-monospace">{liveStatus.plate}</span>
                  </h3>
                  <div className="d-flex align-items-center justify-content-center text-light">
                    <Spinner animation="border" variant="info" className="me-3" />
                    <span className="fs-5">{liveStatus.message}</span>
                  </div>
                </div>
              )}
              
              {/* Database Button Overlay */}
              <div className="position-absolute bottom-0 w-100 pb-4 text-center" style={{ zIndex: 5 }}>
                <Button variant="light" size="lg" onClick={() => setShowModal(true)} className="rounded-pill px-5 fw-bold shadow">
                  View Registered Vehicles Database
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* ========================================== */}
        {/* RIGHT COLUMN: LIVE ORCHESTRATOR FEED */}
        {/* ========================================== */}
        <Col lg={5}>
          <Card className="shadow-sm border-0 h-100">
            <Card.Header className="bg-primary text-white">
              <h6 className="mb-0 py-1">Live Policy Engine Audit Logs</h6>
            </Card.Header>
            <div className="table-responsive" style={{ height: '600px', overflowY: 'auto' }}>
              <Table striped bordered hover className="mb-0 text-center align-middle" style={{ fontSize: '0.85rem' }}>
                <thead className="table-light sticky-top shadow-sm">
                  <tr>
                    <th>Vehicle ID</th>
                    <th>Plate</th>
                    <th>Type</th>
                    <th>Decision</th>
                    <th>System Reason</th>
                  </tr>
                </thead>
                <tbody>
                  
                  {/* DYNAMIC PENDING ROW: Injects instantly when camera detects a plate */}
                  {liveStatus.plate && (
                    <tr className="table-warning border-warning shadow-sm">
                      <td className="text-muted fw-bold">--</td>
                      <td className="fw-bold font-monospace fs-6 text-primary">{liveStatus.plate}</td>
                      <td><Spinner animation="grow" variant="warning" size="sm" /></td>
                      <td>
                        <Badge bg="warning" className="text-dark py-2 px-3">EVALUATING</Badge>
                      </td>
                      <td className="text-start text-dark fw-bold">
                        <em>{liveStatus.message}</em>
                      </td>
                    </tr>
                  )}

                  {/* STANDARD DATABASE LOGS */}
                  {auditLogs.length > 0 ? (
                    auditLogs.map((log, index) => (
                      <tr key={index}>
                        <td className="text-muted">{log.vehicle_id || 'UNREGISTERED'}</td>
                        <td className="fw-bold">{log.plate_number || log.license_plate}</td>
                        <td>{log.vehicle_type || 'Unknown'}</td>
                        <td>
                          <Badge bg={log.policy_decision === 'APPROVED' ? 'success' : 
                                     log.policy_decision === 'REJECTED' ? 'danger' : 'secondary'}>
                            {log.policy_decision || 'PENDING'}
                          </Badge>
                        </td>
                        <td className="text-start text-muted">
                          {log.agent_reasoning || 'Awaiting system evaluation.'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="text-muted py-4">No audit logs recorded yet.</td>
                    </tr>
                  )}
                </tbody>
              </Table>
            </div>
          </Card>
        </Col>
      </Row>

      {/* ========================================== */}
      {/* POPUP MODAL: REGISTERED VEHICLES DB */}
      {/* ========================================== */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
        <Modal.Header closeButton className="bg-dark text-white">
          <Modal.Title>Registered Vehicles Database</Modal.Title>
        </Modal.Header>
        <Modal.Body className="p-0">
          <div className="table-responsive" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            <Table striped hover className="mb-0 text-center align-middle" style={{ fontSize: '0.95rem' }}>
              <thead className="table-light sticky-top shadow-sm">
                <tr>
                  <th>Booking ID</th>
                  <th>Plate</th>
                  <th>Type</th>
                  <th>Payment Status</th>
                </tr>
              </thead>
              <tbody>
                {registrations.length > 0 ? (
                  registrations.map((reg, index) => (
                    <tr key={index}>
                      <td className="text-muted">{reg.booking_id}</td>
                      <td className="fw-bold">{reg.plate_number}</td>
                      <td>{reg.vehicle_type}</td>
                      <td>
                        <Badge bg={reg.is_paid ? 'success' : 'warning'}>
                          {reg.is_paid ? 'Paid' : 'Pending'}
                        </Badge>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="text-muted py-5">No registered vehicles found.</td>
                  </tr>
                )}
              </tbody>
            </Table>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Close Database</Button>
        </Modal.Footer>
      </Modal>

    </Container>
  );
}