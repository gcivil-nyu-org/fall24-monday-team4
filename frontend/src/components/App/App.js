import logo from '../../static/logo.svg';
import './App.css';
import React, { useEffect, useState } from 'react';

function App() {

  const [data, setData] = useState(null);

  useEffect(() => {

    (async () => {
      fetch('http://localhost:8000/testapi/api/data/')
      .then(async (response) => {
        const val = await response.json();
        console.log("val: ", val)
        return val;

  })
      .then((data) => setData(data));
    })();
    
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
      <h1>{data ? data.message : 'Loading...'}</h1>
    </div>
  );
}

export default App;
