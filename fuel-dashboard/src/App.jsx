import { useState, useEffect } from 'react';
import axios from 'axios';
import { Container, Row, Col, Table, Badge, Card, Navbar, Spinner } from 'react-bootstrap';
import './bootstrap.min.css';

function App() {
  const [logs, setLogs] = useState([]);
  const [liveStatus, setLiveStatus] = useState({ plate: null, message: "Waiting for vehicle..." });

  useEffect(() => {
    fetchLogs();
    
    // Poll the database logs every 3 seconds
    const logInterval = setInterval(fetchLogs, 3000);
    // Poll the live AI status every 1 second for real-time UI updates
    const statusInterval = setInterval(fetchLiveStatus, 1000);
    
    return () => {
      clearInterval(logInterval);
      clearInterval(statusInterval);
    };
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await axios.get('http://localhost:8080/api/audit-logs');
      if (response.data.status === 'success') {
        setLogs(response.data.data);
      }
    } catch (error) {
      console.error("Error fetching logs:", error);
    }
  };

  const fetchLiveStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8080/api/live-status');
      setLiveStatus(response.data);
    } catch (error) {
      console.error("Error fetching live status:", error);
    }
  };

  const getStatusBadge = (decision) => {
    if (decision.includes("APPROVED")) return <Badge bg="success">APPROVED</Badge>;
    return <Badge bg="danger">REJECTED</Badge>;
  };

  return (
    <div style={{ backgroundColor: '#f8f9fa', minHeight: '100vh', paddingBottom: '50px' }}>
      <Navbar bg="dark" variant="dark" className="mb-4 shadow-sm">
        <Container>
          <Navbar.Brand className="fw-bold">
            Autonomous Fuel Station 
          </Navbar.Brand>
        </Container>
      </Navbar>

      <Container fluid className="px-4 mt-4">
        <Row>
          {/* LEFT COLUMN: Live Camera Feed with Overlay */}
          <Col lg={7}>
            <Card className="shadow-sm border-0 mb-4">
              <Card.Header className="bg-dark text-white">Live ANPR Camera Feed</Card.Header>
              <Card.Body className="p-0 text-center bg-black position-relative">
                <img 
                  src="http://localhost:8080/api/video-feed" 
                  alt="Live Camera" 
                  style={{ width: '100%', maxHeight: '600px', objectFit: 'contain' }} 
                />
                
                {/* FLOATING OVERLAY: Only shows when a plate is being processed */}
                {liveStatus.plate && (
                  <div className="position-absolute top-50 start-50 translate-middle w-75 p-3 rounded" 
                       style={{ backgroundColor: 'rgba(0, 0, 0, 0.8)', border: '1px solid #0d6efd' }}>
                    <h4 className="text-white mb-3">Target Acquired: <span className="text-info font-monospace">{liveStatus.plate}</span></h4>
                    <div className="d-flex align-items-center justify-content-center text-light">
                      <Spinner animation="border" variant="info" size="sm" className="me-2" />
                      <span>{liveStatus.message}</span>
                    </div>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>

          {/* RIGHT COLUMN: The Audit Table */}
          <Col lg={5}>
            <Card className="shadow-sm border-0">
              <Card.Header className="bg-white border-bottom-0 pt-4 pb-0">
                <h5 className="mb-0 text-primary">Live Policy Engine Audit Logs</h5>
                <small className="text-muted">Auto-syncing with Master Orchestrator</small>
              </Card.Header>
              <Card.Body>
                <Table responsive hover className="mt-3">
                  <thead className="table-light">
                    <tr>
                      <th>ID</th>
                      <th>Timestamp</th>
                      <th>License Plate</th>
                      <th>Policy Decision</th>
                      <th>Agent Reasoning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* DYNAMIC PENDING ROW: Shows immediately when plate is extracted */}
                    {liveStatus.plate && (
                      <tr className="table-warning">
                        <td className="align-middle fw-bold text-secondary">--</td>
                        <td className="align-middle text-muted">LIVE</td>
                        <td className="align-middle font-monospace fs-6 fw-bold">{liveStatus.plate}</td>
                        <td className="align-middle">
                          <Spinner animation="grow" variant="warning" size="sm" />
                        </td>
                        <td className="align-middle text-muted" style={{ fontSize: '0.85rem' }}>
                          <em>{liveStatus.message}</em>
                        </td>
                      </tr>
                    )}

                    {/* STANDARD DATABASE LOGS */}
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td className="align-middle fw-bold text-secondary">#{log.id}</td>
                        <td className="align-middle text-muted">
                          {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                        </td>
                        <td className="align-middle font-monospace fs-6">{log.plate_number}</td>
                        <td className="align-middle">{getStatusBadge(log.decision)}</td>
                        <td className="align-middle" style={{ fontSize: '0.85rem', maxWidth: '300px' }}>
                          {log.reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
}

export default App;