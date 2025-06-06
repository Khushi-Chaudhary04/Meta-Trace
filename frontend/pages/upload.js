import Navbar from '@/components/Navbar';
import Head from 'next/head';
import { useState, useEffect } from 'react';
import { CloudUpload } from 'lucide-react';
import Footer from '@/components/Footer';
import RecentUploads from '@/components/RecentUploads';
import MetadataModal from '@/components/MetadataModal';
import { useRouter } from 'next/router';
import MetadataAndRecommendations from '@/components/MetadataRecommendations';
import UploadLoader from '@/components/UploadLoader';
import Web3 from 'web3';
import axios from 'axios';

const Upload = () => {
  const router = useRouter();

  const [file, setFile] = useState(null);
  const [fileEnter, setFileEnter] = useState(false);
  const [recentUploads, setRecentUploads] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [userEmail, setUserEmail] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedFileMetadata, setSelectedFileMetadata] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  const [recentUploadMetadata, setRecentUploadMetadata] = useState(null);

  // Smart contract details
  const contractAddress = '0x791282CEa8B65442C9A10AF844bc364ADfb751b0';
  const contractABI = [
    {
      inputs: [
        { internalType: 'address', name: 'to', type: 'address' },
        { internalType: 'string', name: 'uri', type: 'string' }
      ],
      name: 'mint',
      outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
      stateMutability: 'nonpayable',
      type: 'function'
    },
    // ... (rest of the ABI objects, omitted for brevity)
    {
      inputs: [],
      name: 'totalSupply',
      outputs: [{ internalType: 'uint256', name: '', type: 'uint256' }],
      stateMutability: 'view',
      type: 'function'
    }
  ];

  useEffect(() => {
    fetchUserEmail();
  }, []);

  useEffect(() => {
    if (userEmail) {
      fetchUploadedFiles();
    }
  }, [userEmail]);

  // Fetch logged-in user email from API
  const fetchUserEmail = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    try {
      const response = await fetch('/api/auth/profile', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Failed to fetch user profile');
      const userData = await response.json();
      setUserEmail(userData.email);
    } catch {
      router.push('/login');
    }
  };

  // Validate allowed file types and extensions
  const validateFileType = (file) => {
    if (!file) return false;
    const allowedFileTypes = [
      'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/svg+xml',
      'application/pdf', 'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain', 'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv', 'video/mp4', 'video/webm', 'video/quicktime', 'audio/mpeg',
      'audio/wav', 'audio/ogg', 'application/zip', 'application/x-tar', 'application/gzip'
    ];
    const validExtensions = [
      '.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf', '.doc', '.docx', '.txt',
      '.xls', '.xlsx', '.csv', '.mp4', '.webm', '.mov', '.mp3', '.wav', '.ogg',
      '.zip', '.tar', '.gz', '.webp'
    ];
    const fileExtension = `.${file.name.split('.').pop().toLowerCase()}`;
    return allowedFileTypes.includes(file.type) || validExtensions.includes(fileExtension);
  };

  // Fetch recent uploads for user
  const fetchUploadedFiles = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/upload?email=${encodeURIComponent(userEmail)}`);
      if (!response.ok) throw new Error('Failed to fetch uploads');
      const data = await response.json();
      const sortedFiles = data.files.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      setRecentUploads(sortedFiles.slice(0, 5));
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Handle input file change or drag & drop
  const handleFileChange = async (e) => {
    const uploadedFile = e.target.files[0];
    if (!uploadedFile) return;

    if (!validateFileType(uploadedFile)) {
      alert('Unsupported file type. Please upload a valid file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('email', userEmail);

    setUploading(true);
    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Upload failed');

      setSelectedFileMetadata({ ...data.metadata, filename: uploadedFile.name });
      setShowMetadata(true);
      fetchUploadedFiles();
      setFile(uploadedFile);
    } catch (error) {
      alert('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  // Handle drag and drop file upload
  const handleFileDrop = (e) => {
    e.preventDefault();
    setFileEnter(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const syntheticEvent = { target: { files: [droppedFile] } };
      handleFileChange(syntheticEvent);
    }
  };

  // Mint NFT on blockchain with metadata URI

const handleMintNFT = async () => {
  if (!selectedFileMetadata || !file) {
    alert('No file or metadata found');
    return;
  }

  try {
    if (!window.ethereum) throw new Error('MetaMask not found');

    const web3 = new Web3(window.ethereum);
    await window.ethereum.request({ method: 'eth_requestAccounts' });
    const accounts = await web3.eth.getAccounts();
    const userAccount = accounts[0];

    // Upload image to IPFS
    const pinataApiKey = '25b25147c472c196555d';
    const pinataSecretApiKey = '4162fa758e5b1cc705b97cc91ab58bb88b956db07d8044c8a75840fbf57dae24';

    const imageFormData = new FormData();
    imageFormData.append('file', file);

    const imageUploadRes = await axios.post(
      'https://api.pinata.cloud/pinning/pinFileToIPFS',
      imageFormData,
      {
        maxBodyLength: 'Infinity',
        headers: {
          'Content-Type': 'multipart/form-data',
          pinata_api_key: pinataApiKey,
          pinata_secret_api_key: pinataSecretApiKey
        }
      }
    );

    const imageHash = imageUploadRes.data.IpfsHash;
    const imageUrl = `https://gateway.pinata.cloud/ipfs/${imageHash}`;

    // Format attributes for NFT
    const attributes = Object.entries(selectedFileMetadata).map(([key, value]) => ({
      trait_type: key,
      value: value
    }));

    // Metadata JSON for NFT
    const metadata = {
      name: selectedFileMetadata.filename || "Ecovisit",
      description: "Metadata generated by MetaTrace platform",
      image: imageUrl,
      attributes: attributes
    };

    // Upload metadata to IPFS
    const metadataRes = await axios.post(
      'https://api.pinata.cloud/pinning/pinJSONToIPFS',
      {
        pinataMetadata: {
          name: metadata.name
        },
        pinataContent: metadata
      },
      {
        headers: {
          'Content-Type': 'application/json',
          pinata_api_key: pinataApiKey,
          pinata_secret_api_key: pinataSecretApiKey
        }
      }
    );

    const metadataHash = metadataRes.data.IpfsHash;
    const tokenURI = `https://gateway.pinata.cloud/ipfs/${metadataHash}`;

    // Mint NFT with contract
    const contract = new web3.eth.Contract(contractABI, contractAddress);
    await contract.methods
      .mint(userAccount, tokenURI)
      .send({ from: userAccount });

    alert("✅ NFT minted successfully!");
  } catch (err) {
    console.error('Minting error:', err);
    alert('❌ Minting failed.');
  }
};


  // Open modal with metadata details
  const handleMetadataClick = (metadata) => {
    setRecentUploadMetadata(metadata);
    setIsModalOpen(true);
  };

  // Close metadata modal
  const handleModalClose = () => {
    setIsModalOpen(false);
    setRecentUploadMetadata(null);
  };

  // Delete uploaded file by ID
  const handleDelete = async (uploadId) => {
    if (!uploadId) return;
    try {
      setLoading(true);
      const response = await fetch(`/api/upload/${uploadId}`, { method: 'DELETE' });
      if (response.ok) {
        await fetchUploadedFiles();
        setIsModalOpen(false);
      } else {
        alert('Failed to delete the file.');
      }
    } catch {
      alert('Error deleting the file.');
    } finally {
      setLoading(false);
    }
  };

  // Delete from modal, reuse handleDelete
  const handleModDelete = (uploadId) => {
    handleDelete(uploadId);
  };

  return (
    <>
      <Head>
        <title>Upload your File | MetaTrace</title>
      </Head>

      <div className="min-h-screen bg-[#f7f7f7]">
        <Navbar />

        <div className="px-9 flex flex-col py-8 justify-center">
          {showMetadata ? (
            <MetadataAndRecommendations
              metadata={selectedFileMetadata}
              onBackToUpload={() => setShowMetadata(false)}
              onMintNFT={handleMintNFT}
            />
          ) : uploading ? (
            <div className="flex items-center justify-center h-full">
              <UploadLoader />
            </div>
          ) : (
            <div className="upload-container">
              <h2 className="text-3xl font-black mb-2 epilogue text-center">
                Upload Your <span className="text-[#f74b25ff]">File</span>
              </h2>
              <p className="text-[#5e5e5eff] poppins mb-4 text-lg text-center">
                Securely upload and manage your files in one place.
              </p>

              <div
                onClick={() => document.getElementById('file-upload').click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setFileEnter(true);
                }}
                onDragLeave={() => setFileEnter(false)}
                onDrop={handleFileDrop}
                className={`border-dashed border-2 rounded-lg p-8 w-full flex flex-col items-center justify-center cursor-pointer transition-all ${
                  fileEnter ? 'border-[#1b1b1cff] bg-[#fbb3a3]' : 'border-[#1b1b1cff] bg-[#fbb3a3]'
                }`}
              >
                <CloudUpload className="w-16 h-16 text-[#1c1c1cff] mb-4" />
                <p className="text-[#1c1c1cff] font-semibold poppins">
                  Drag & drop your files here or click to upload
                </p>
                <input type="file" onChange={handleFileChange} className="hidden" id="file-upload" />
              </div>
            </div>
          )}

          <RecentUploads
            uploads={recentUploads}
            onMetadataClick={handleMetadataClick}
            onDelete={handleDelete}
            loading={loading}
          />

          <MetadataModal
            isOpen={isModalOpen}
            fileMetadata={recentUploadMetadata}
            onClose={handleModalClose}
            onDelete={handleModDelete}
          />
        </div>

        <Footer />
      </div>
    </>
  );
};

export default Upload;
