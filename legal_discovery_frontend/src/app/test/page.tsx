export default function TestPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">✅ Frontend Test Page</h1>
      <p className="mt-4">If you can see this, the frontend is working!</p>
      <div className="mt-4 p-4 bg-green-100 rounded">
        <p>Next.js is running successfully</p>
        <p>Time: {new Date().toLocaleString()}</p>
      </div>
    </div>
  )
}