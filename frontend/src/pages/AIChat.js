import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import { Navbar } from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Send, Plus, MessageSquare, Image, Video, Globe, 
  Loader2, Download, Trash2, Mic, ChevronLeft, ChevronRight, Sparkles,
  Volume2, VolumeX, Copy, Check, Play, X, ArrowUp,
  Code, Eye, EyeOff, Gamepad2, RefreshCw, Maximize2, Minimize2,
  Coins, Gift, Paperclip, Zap, Save, GitFork, Settings2, Bot,
  Layout, Rocket, Link, ExternalLink, BookMarked, Upload, Share2, FileText,
  Smartphone
} from 'lucide-react';

// ============== Zitex Logo Animation ==============
const ZITEX_LOGO_URL = "https://static.prod-images.emergentagent.com/jobs/d28c1cbc-c039-46df-a176-2e32ebb0f715/images/f7f88c5a96c3a3978fb84a31dd4d6b922be1568a9083c93bf3cef363e8c17387.png";

const ZitexLogo = memo(({ isAnimating, size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };
  
  return (
    <div className={`${sizeClasses[size]} relative flex-shrink-0`}>
      <img 
        src={ZITEX_LOGO_URL} 
        alt="Zitex" 
        className={`w-full h-full object-contain rounded-full ${isAnimating ? 'animate-spin-slow' : ''}`}
      />
      {isAnimating && (
        <div className="absolute inset-0 rounded-full bg-amber-500/20 animate-ping" />
      )}
    </div>
  );
});

// ============== Code Block with Copy ==============
const CodeBlock = memo(({ code, language = 'html', filename }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    toast.success('تم نسخ الكود!');
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="my-3 rounded-xl overflow-hidden bg-[#0d1117] border border-slate-700/50">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Code className="w-4 h-4 text-purple-400" />
          <span className="text-xs text-gray-400 font-mono">{filename || language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all hover:bg-slate-700/50"
          style={{ color: copied ? '#10b981' : '#94a3b8' }}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'تم!' : 'نسخ'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm max-h-96">
        <code className="text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">{code}</code>
      </pre>
    </div>
  );
});

// ============== Message Content Parser ==============
const parseMessageContent = (content, metadata = {}) => {
  if (!content) return [];
  const parts = [];
  
  // First, remove CODE_BLOCK from display (code goes to Live Preview only)
  let displayContent = content.replace(/\[CODE_BLOCK\]\s*```[\s\S]*?```\s*\[\/CODE_BLOCK\]/g, '');
  // Also handle [CODES_BLOCK] and other variations
  displayContent = displayContent.replace(/\[CODE\w*_?BLOCK\]\s*```[\s\S]*?```\s*\[\/CODE\w*_?BLOCK\]/g, '');
  displayContent = displayContent.replace(/\[CODE\w*_?BLOCK\]\s*[\s\S]*?\[\/CODE\w*_?BLOCK\]/g, '');
  
  // Remove raw HTML blocks that are code output (<!DOCTYPE...>)
  displayContent = displayContent.replace(/<!DOCTYPE\s+html[\s\S]*?<\/html>/gi, '');
  
  // Also remove any regular code blocks from display (they go to preview)
  displayContent = displayContent.replace(/```(?:html|javascript|js)?\n?[\s\S]*?```/g, '');
  
  // Extract buttons
  const buttonRegex = /\[BUTTONS\]\n?([\s\S]*?)\[\/BUTTONS\]/g;
  
  let processedContent = displayContent;
  
  // Extract buttons
  let buttonMatch;
  while ((buttonMatch = buttonRegex.exec(displayContent)) !== null) {
    const buttonText = buttonMatch[1].trim();
    const buttons = buttonText.split('|').map(b => b.trim()).filter(b => b);
    processedContent = processedContent.replace(buttonMatch[0], `__BUTTONS__${JSON.stringify(buttons)}__ENDBUTTONS__`);
  }
  
  // Now parse the rest
  let lastIndex = 0;
  let match;
  
  // Handle buttons
  const combinedRegex = /__BUTTONS__([\s\S]*?)__ENDBUTTONS__/g;
  
  while ((match = combinedRegex.exec(processedContent)) !== null) {
    if (match.index > lastIndex) {
      const textBefore = processedContent.slice(lastIndex, match.index).trim();
      if (textBefore) {
        parts.push({ type: 'text', content: textBefore });
      }
    }
    
    if (match[1]) {
      // Buttons
      try {
        const buttons = JSON.parse(match[1]);
        parts.push({ type: 'buttons', buttons });
      } catch (e) {
        parts.push({ type: 'text', content: match[0] });
      }
    }
    
    lastIndex = match.index + match[0].length;
  }
  
  if (lastIndex < processedContent.length) {
    const remaining = processedContent.slice(lastIndex).trim();
    if (remaining) {
      parts.push({ type: 'text', content: remaining });
    }
  }
  
  // If we have preview, add indicator
  if (metadata?.has_preview) {
    parts.push({ type: 'preview_indicator' });
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content: displayContent.trim() || content }];
};

// ============== Preview Indicator Component ==============
const PreviewIndicator = memo(() => (
  <div className="mt-3 p-3 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-xl flex items-center gap-3">
    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
      <Eye className="w-5 h-5 text-green-400" />
    </div>
    <div>
      <p className="text-green-300 text-sm font-medium">شاهد النتيجة في المعاينة المباشرة ←</p>
      <p className="text-green-400/60 text-xs">يمكنك التفاعل مع الموقع مباشرة</p>
    </div>
  </div>
));

// ============== Choice Buttons Component ==============
const ChoiceButtons = memo(({ buttons, onSelect }) => (
  <div className="flex flex-wrap gap-2 mt-3">
    {buttons.map((btn, idx) => (
      <button
        key={idx}
        onClick={() => onSelect(btn)}
        className="px-4 py-2 bg-gradient-to-r from-amber-500/20 to-yellow-500/20 hover:from-amber-500/30 hover:to-yellow-500/30 border border-amber-500/40 hover:border-amber-400 text-amber-200 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-amber-500/20"
      >
        {btn}
      </button>
    ))}
  </div>
));

// ============== File Upload Component ==============
const FileUploadButton = memo(({ onFileSelect }) => {
  const fileInputRef = useRef(null);
  
  const handleClick = () => fileInputRef.current?.click();
  
  const handleChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Check file size (50MB limit)
    if (file.size > 50 * 1024 * 1024) {
      toast.error('حجم الملف أكبر من 50 MB');
      return;
    }
    
    onFileSelect(file);
    e.target.value = ''; // Reset input
  };
  
  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="image/*,video/*,.pdf,.doc,.docx,.txt,audio/*"
        onChange={handleChange}
      />
      <Button
        size="icon"
        variant="ghost"
        onClick={handleClick}
        className="h-9 w-9 text-gray-400 hover:text-amber-400 hover:bg-amber-500/10"
        title="رفع ملف"
      >
        <Upload className="w-4 h-4" />
      </Button>
    </>
  );
});

// ============== Social Media Export Modal ==============
const SOCIAL_PLATFORMS = [
  { id: 'tiktok', name: 'TikTok', icon: '🎵', color: 'from-pink-500 to-purple-500' },
  { id: 'snapchat', name: 'Snapchat', icon: '👻', color: 'from-yellow-400 to-yellow-500' },
  { id: 'instagram_reels', name: 'Instagram Reels', icon: '📸', color: 'from-purple-500 to-pink-500' },
  { id: 'instagram_story', name: 'Instagram Story', icon: '📱', color: 'from-orange-500 to-pink-500' },
  { id: 'instagram_post', name: 'Instagram Post', icon: '🖼️', color: 'from-pink-500 to-orange-500' },
  { id: 'youtube_shorts', name: 'YouTube Shorts', icon: '▶️', color: 'from-red-500 to-red-600' },
  { id: 'facebook', name: 'Facebook', icon: '📘', color: 'from-blue-600 to-blue-700' },
  { id: 'twitter', name: 'Twitter/X', icon: '🐦', color: 'from-blue-400 to-blue-500' }
];

const SocialExportModal = memo(({ isOpen, onClose, assetId, assetUrl, assetType }) => {
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [exportResults, setExportResults] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const API_URL = process.env.REACT_APP_BACKEND_URL;
  
  const togglePlatform = (platformId) => {
    setSelectedPlatforms(prev => 
      prev.includes(platformId) 
        ? prev.filter(p => p !== platformId)
        : [...prev, platformId]
    );
  };
  
  const handleExport = async () => {
    if (selectedPlatforms.length === 0) {
      toast.error('اختر منصة واحدة على الأقل');
      return;
    }
    
    setIsExporting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/social/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          asset_id: assetId,
          platforms: selectedPlatforms
        })
      });
      
      const data = await response.json();
      if (response.ok) {
        setExportResults(data.exports);
        toast.success('تم تجهيز الملفات للتصدير!');
      } else {
        toast.error(data.detail || 'فشل التصدير');
      }
    } catch (error) {
      toast.error('خطأ في الاتصال');
    } finally {
      setIsExporting(false);
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between bg-gradient-to-r from-purple-500/10 to-pink-500/10">
          <div className="flex items-center gap-3">
            <Share2 className="w-6 h-6 text-purple-400" />
            <div>
              <h2 className="text-lg font-bold text-white">تصدير للمنصات الاجتماعية</h2>
              <p className="text-xs text-gray-400">مجاني - اختر المنصات المطلوبة</p>
            </div>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {!exportResults ? (
            <>
              {/* Platform Selection */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {SOCIAL_PLATFORMS.map(platform => (
                  <button
                    key={platform.id}
                    onClick={() => togglePlatform(platform.id)}
                    className={`p-3 rounded-xl border-2 transition-all ${
                      selectedPlatforms.includes(platform.id)
                        ? `bg-gradient-to-br ${platform.color} border-transparent text-white shadow-lg`
                        : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 text-gray-300'
                    }`}
                  >
                    <span className="text-2xl block mb-1">{platform.icon}</span>
                    <span className="text-xs font-medium">{platform.name}</span>
                  </button>
                ))}
              </div>
              
              {/* Export Button */}
              <div className="mt-6">
                <Button
                  onClick={handleExport}
                  disabled={isExporting || selectedPlatforms.length === 0}
                  className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 h-12 text-lg"
                >
                  {isExporting ? (
                    <><Loader2 className="w-5 h-5 animate-spin me-2" /> جاري التجهيز...</>
                  ) : (
                    <><Share2 className="w-5 h-5 me-2" /> تصدير ({selectedPlatforms.length})</>
                  )}
                </Button>
              </div>
            </>
          ) : (
            /* Export Results */
            <div className="space-y-3">
              {exportResults.map(result => (
                <div key={result.platform} className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{result.icon}</span>
                    <div className="flex-1">
                      <h4 className="font-medium text-white">{result.platform_name}</h4>
                      <p className="text-xs text-gray-400">
                        {result.specs.width}x{result.specs.height} • {result.specs.aspect}
                      </p>
                    </div>
                    {result.download_url && (
                      <a
                        href={result.download_url}
                        download
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-sm font-medium hover:bg-green-500/30 flex items-center gap-1"
                      >
                        <Download className="w-4 h-4" /> تحميل
                      </a>
                    )}
                  </div>
                  {/* Tips */}
                  <div className="space-y-1">
                    {result.tips?.map((tip, i) => (
                      <p key={i} className="text-xs text-amber-300/80 flex items-start gap-2">
                        <span className="text-amber-400">💡</span> {tip}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
              
              <Button
                onClick={() => { setExportResults(null); setSelectedPlatforms([]); }}
                variant="outline"
                className="w-full mt-4"
              >
                تصدير لمنصات أخرى
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

// ============== Uploaded File Preview ==============
const UploadedFilePreview = memo(({ file, onRemove, onSend }) => (
  <div className="mx-4 mb-2 p-3 bg-slate-800/70 border border-slate-700 rounded-xl flex items-center gap-3">
    {file.type.startsWith('image/') ? (
      <img src={URL.createObjectURL(file)} alt="Preview" className="w-14 h-14 object-cover rounded-lg" />
    ) : file.type.startsWith('video/') ? (
      <div className="w-14 h-14 bg-orange-500/20 rounded-lg flex items-center justify-center">
        <Video className="w-6 h-6 text-orange-400" />
      </div>
    ) : file.type.startsWith('audio/') ? (
      <div className="w-14 h-14 bg-purple-500/20 rounded-lg flex items-center justify-center">
        <Volume2 className="w-6 h-6 text-purple-400" />
      </div>
    ) : (
      <div className="w-14 h-14 bg-blue-500/20 rounded-lg flex items-center justify-center">
        <FileText className="w-6 h-6 text-blue-400" />
      </div>
    )}
    <div className="flex-1 min-w-0">
      <p className="text-white text-sm truncate">{file.name}</p>
      <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
    </div>
    <Button size="icon" variant="ghost" onClick={onRemove} className="text-red-400 hover:bg-red-500/20">
      <X className="w-4 h-4" />
    </Button>
    <Button onClick={onSend} className="bg-amber-500 hover:bg-amber-600 text-black">
      <Send className="w-4 h-4 me-1" /> أرسل
    </Button>
  </div>
));

// ============== Session Skeleton ==============
const SessionSkeleton = () => (
  <div className="space-y-2 p-2">
    {[1, 2, 3].map(i => (
      <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-slate-800/30 animate-pulse">
        <div className="w-8 h-8 rounded-lg bg-slate-700/50" />
        <div className="flex-1">
          <div className="h-3 w-3/4 mb-2 bg-slate-700/50 rounded" />
          <div className="h-2 w-1/2 bg-slate-700/50 rounded" />
        </div>
      </div>
    ))}
  </div>
);

// ============== Session Item ==============
const SessionItem = memo(({ session, isActive, onSelect, onDelete, getIcon }) => (
  <div
    className={`group flex items-center gap-2 p-2.5 rounded-xl cursor-pointer transition-all duration-200 ${
      isActive 
        ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30' 
        : 'hover:bg-slate-800/50 border border-transparent'
    }`}
    onClick={() => onSelect(session.id)}
    data-testid={`session-${session.id}`}
  >
    <div className={`p-1.5 rounded-lg ${
      session.session_type === 'image' ? 'bg-purple-500/20 text-purple-400' :
      session.session_type === 'video' ? 'bg-orange-500/20 text-orange-400' :
      session.session_type === 'website' ? 'bg-green-500/20 text-green-400' :
      session.session_type === 'game' ? 'bg-cyan-500/20 text-cyan-400' :
      'bg-slate-700/50 text-gray-400'
    }`}>
      {getIcon(session.session_type)}
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-white text-sm truncate">{session.title}</p>
      <p className="text-[10px] text-gray-500">{session.message_count || 0} رسالة</p>
    </div>
    <Button
      size="icon"
      variant="ghost"
      onClick={(e) => { e.stopPropagation(); onDelete(session.id); }}
      className="opacity-0 group-hover:opacity-100 h-6 w-6 text-gray-500 hover:text-red-400"
    >
      <Trash2 className="w-3 h-3" />
    </Button>
  </div>
));

// ============== Chat Message ==============
const ChatMessage = memo(({ msg, idx, renderAttachment, onPlayAudio, onGenerateTTS, playingAudio, onPreview, isTyping, onButtonClick }) => {
  const parsedContent = parseMessageContent(msg.content, msg.metadata);
  const hasButtons = parsedContent.some(p => p.type === 'buttons');
  const hasPreviewIndicator = parsedContent.some(p => p.type === 'preview_indicator');
  const isUser = msg.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-start' : 'justify-end'} animate-fadeIn`} data-testid={`message-${idx}`}>
      {/* User Message */}
      {isUser ? (
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
            U
          </div>
          <div className="bg-slate-800/80 backdrop-blur border border-slate-700/50 rounded-2xl rounded-tl-md p-4 shadow-lg">
            {parsedContent.map((part, i) => (
              part.type === 'buttons' ? null : 
              part.type === 'preview_indicator' ? null :
              <p key={i} className="text-white whitespace-pre-wrap leading-relaxed text-sm">{part.content}</p>
            ))}
            <p className="text-[10px] text-gray-500 mt-2">
              {new Date(msg.created_at).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      ) : (
        /* AI Message */
        <div className="flex items-start gap-3 max-w-[85%]">
          <div className="order-2">
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl rounded-tr-md p-4 shadow-xl">
              {parsedContent.map((part, i) => (
                part.type === 'buttons' ? (
                  <ChoiceButtons key={i} buttons={part.buttons} onSelect={onButtonClick} />
                ) : part.type === 'preview_indicator' ? (
                  <PreviewIndicator key={i} />
                ) : (
                  <p key={i} className="text-gray-200 whitespace-pre-wrap leading-relaxed text-sm">{part.content}</p>
                )
              ))}
              
              {/* Attachments */}
              {msg.attachments?.map((attachment, aIdx) => (
                <div key={aIdx}>{renderAttachment(attachment, onPreview)}</div>
              ))}
              
              {/* Footer - hide if only buttons */}
              {!hasButtons && (
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-700/30">
                  <p className="text-[10px] text-gray-500">
                    {new Date(msg.created_at).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                  <div className="flex items-center gap-1">
                    {msg.metadata?.credits_used > 0 && (
                      <span className="text-[10px] text-amber-400/60 mr-2">
                        -{msg.metadata.credits_used} نقطة
                      </span>
                    )}
                    <button
                      onClick={() => msg.audio_url ? onPlayAudio(msg.audio_url, msg.id) : onGenerateTTS(msg.content, msg.id)}
                      className={`p-1.5 rounded-lg transition-all ${
                        playingAudio === msg.id ? 'bg-purple-500 text-white' : 'text-gray-400 hover:bg-slate-700'
                      }`}
                    >
                      {playingAudio === msg.id ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
          <ZitexLogo size="sm" isAnimating={isTyping} />
        </div>
      )}
    </div>
  );
});

// ============== Live Preview Panel ==============
const LivePreviewPanel = memo(({ code, isOpen, onClose, onRefresh, isFullscreen, onToggleFullscreen, onExportCode, userCredits, onSaveTemplate, onDeploy, currentSession }) => {
  const iframeRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [subdomain, setSubdomain] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    if (code && iframeRef.current) {
      const iframe = iframeRef.current;
      const doc = iframe.contentDocument || iframe.contentWindow.document;
      // iframe with about:blank can't resolve relative /api/* URLs — rewrite to absolute backend URL
      const backend = process.env.REACT_APP_BACKEND_URL || '';
      let patched = code;
      if (backend) {
        // HTML attributes: src="/api/..." href="/api/..."
        patched = patched.replace(/(src|href)=["'](\/api\/[^"']+)["']/g, `$1="${backend}$2"`);
        // CSS url(...) — with or without quotes
        patched = patched.replace(/url\((["']?)(\/api\/[^)"']+)\1\)/g, `url($1${backend}$2$1)`);
      }
      doc.open();
      doc.write(patched);
      doc.close();
    }
  }, [code]);
  
  const handleCopyCode = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    toast.success('تم نسخ الكود!');
    setTimeout(() => setCopied(false), 2000);
  };
  
  const handleDeploy = async () => {
    if (!subdomain.trim()) {
      toast.error('أدخل اسم النطاق');
      return;
    }
    setDeploying(true);
    try {
      await onDeploy(subdomain);
      setShowDeployModal(false);
      setSubdomain('');
    } catch (e) {
      // Error handled in parent
    } finally {
      setDeploying(false);
    }
  };
  
  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      toast.error('أدخل اسم القالب');
      return;
    }
    setSaving(true);
    try {
      await onSaveTemplate(templateName);
      setShowTemplateModal(false);
      setTemplateName('');
    } catch (e) {
      // Error handled in parent
    } finally {
      setSaving(false);
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : 'h-full'} bg-slate-900 flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-slate-800/80 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
          </div>
          <span className="text-sm text-gray-400 font-medium">Live Preview</span>
          {code && (
            <span className="text-xs text-green-400 bg-green-500/20 px-2 py-0.5 rounded-full">متصل</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {code && (
            <>
              {/* Save as Template */}
              <button 
                onClick={() => setShowTemplateModal(true)} 
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium hover:bg-slate-700 text-gray-400 hover:text-white transition-all"
                title="حفظ كقالب (10 نقاط)"
              >
                <BookMarked className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">قالب</span>
              </button>
              
              {/* Deploy */}
              <button 
                onClick={() => setShowDeployModal(true)} 
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-all"
                title="نشر على الإنترنت (100 نقطة)"
              >
                <Rocket className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">نشر</span>
              </button>
              
              <button 
                onClick={handleCopyCode} 
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium hover:bg-slate-700 text-gray-400 hover:text-white transition-all"
                title="نسخ الكود"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span className="hidden sm:inline">{copied ? 'تم!' : 'نسخ'}</span>
              </button>
              <button 
                onClick={onExportCode} 
                className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 transition-all"
                title="تصدير الكود (50 نقطة)"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">تصدير</span>
              </button>
            </>
          )}
          <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-white transition-all">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={onToggleFullscreen} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-white transition-all">
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 hover:text-red-400 transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Deployment Info Bar */}
      {currentSession?.deployment && (
        <div className="px-3 py-2 bg-green-500/10 border-b border-green-500/20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Rocket className="w-4 h-4 text-green-400" />
            <span className="text-green-300 text-sm">منشور على:</span>
            <a href={currentSession.deployment.url} target="_blank" rel="noopener noreferrer" className="text-green-400 hover:underline flex items-center gap-1">
              {currentSession.deployment.url}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      )}
      
      {/* Preview */}
      <div className="flex-1 bg-white overflow-hidden">
        {code ? (
          <iframe ref={iframeRef} className="w-full h-full border-0" title="Live Preview" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
        ) : (
          <div className="h-full flex items-center justify-center bg-slate-900 text-gray-500">
            <div className="text-center">
              <Eye className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg mb-2">المعاينة المباشرة</p>
              <p className="text-sm text-gray-600">سيظهر المشروع هنا أثناء البناء</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Deploy Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-md mx-4 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
              <Rocket className="w-6 h-6 text-green-400" />
              نشر المشروع
            </h3>
            <p className="text-gray-400 text-sm mb-4">سيتم نشر مشروعك على رابط دائم</p>
            
            <div className="mb-4">
              <label className="text-gray-300 text-sm mb-2 block">اختر اسم النطاق</label>
              <div className="flex items-center bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
                <span className="px-3 text-gray-500 text-sm">https://</span>
                <input
                  type="text"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  placeholder="my-project"
                  className="flex-1 bg-transparent text-white px-2 py-3 text-sm focus:outline-none"
                />
                <span className="px-3 text-gray-500 text-sm">.zitex.app</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">حروف إنجليزية صغيرة وأرقام وشرطات فقط</p>
            </div>
            
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 mb-4">
              <p className="text-amber-300 text-sm flex items-center gap-2">
                <Coins className="w-4 h-4" />
                التكلفة: <strong>100 نقطة</strong>
              </p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => setShowDeployModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-xl text-white transition-all"
              >
                إلغاء
              </button>
              <button
                onClick={handleDeploy}
                disabled={deploying || !subdomain.trim()}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 rounded-xl text-white font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {deploying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
                {deploying ? 'جاري النشر...' : 'نشر الآن'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Save Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-md mx-4 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
              <BookMarked className="w-6 h-6 text-purple-400" />
              حفظ كقالب
            </h3>
            <p className="text-gray-400 text-sm mb-4">احفظ هذا التصميم كقالب لاستخدامه لاحقاً</p>
            
            <div className="mb-4">
              <label className="text-gray-300 text-sm mb-2 block">اسم القالب</label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="مثال: متجر إلكتروني أزرق"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-purple-500"
              />
            </div>
            
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3 mb-4">
              <p className="text-purple-300 text-sm flex items-center gap-2">
                <Coins className="w-4 h-4" />
                التكلفة: <strong>10 نقاط</strong>
              </p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => setShowTemplateModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-xl text-white transition-all"
              >
                إلغاء
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={saving || !templateName.trim()}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-xl text-white font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookMarked className="w-4 h-4" />}
                {saving ? 'جاري الحفظ...' : 'حفظ القالب'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

// ============== Credits Banner ==============
const CreditsBanner = memo(({ credits, isOwner, onBuyCredits }) => {
  if (isOwner) return null;
  
  const percentage = Math.min(100, Math.max(0, ((credits || 0) / 1000) * 100));
  const isLow = percentage < 30;
  
  if (!isLow) return null;
  
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl mb-3">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-400" />
        <span className="text-sm text-amber-200">نقاطك تنفذ؟ اشتري المزيد بخصم 44%...</span>
      </div>
      <button 
        onClick={onBuyCredits}
        className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full text-white text-xs font-medium hover:from-green-600 hover:to-emerald-600 transition-all"
      >
        <Coins className="w-3 h-3" />
        Credits {Math.round(percentage)}% more
      </button>
      <button className="text-gray-500 hover:text-white transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
});

// ============== Main Component ==============
const AIChat = ({ user }) => {
  // State
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false); // مخفي بشكل افتراضي
  const [isTyping, setIsTyping] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [userCredits, setUserCredits] = useState(user?.credits || 0);
  const [ultraMode, setUltraMode] = useState(false);
  
  // Templates State
  const [templates, setTemplates] = useState([]);
  const [showTemplatesPanel, setShowTemplatesPanel] = useState(false);
  
  // Preview State
  const [previewCode, setPreviewCode] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFullscreen, setPreviewFullscreen] = useState(false);
  
  // TTS Settings
  const [ttsSettings, setTtsSettings] = useState({
    enabled: false,
    provider: 'openai',
    voice: 'alloy',
    speed: 1.0
  });
  
  // File Upload State
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  // Social Export State
  const [showSocialExport, setShowSocialExport] = useState(false);
  const [exportAsset, setExportAsset] = useState(null);
  
  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const audioRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioChunksRef = useRef([]);
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [inputMessage]);

  useEffect(() => {
    fetchSessions();
    fetchUserCredits();
    fetchTemplates();
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    };
  }, [mediaRecorder]);

  const fetchTemplates = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.templates || []);
      }
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  }, []);

  const handleUseTemplate = useCallback(async (templateId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/templates/use`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: templateId })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        toast.success(`تم تحميل القالب: ${data.template_name}`);
        setPreviewCode(data.code);
        setPreviewOpen(true);
        setShowTemplatesPanel(false);
        if (data.cost > 0 && user?.role !== 'owner') {
          setUserCredits(prev => Math.max(0, prev - data.cost));
        }
        // Fetch and load the session
        const sessionRes = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${data.session_id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (sessionRes.ok) {
          const sessionData = await sessionRes.json();
          setCurrentSession(sessionData);
          setMessages(sessionData.messages || []);
          setSessions(prev => {
            const exists = prev.find(s => s.id === sessionData.id);
            if (!exists) return [sessionData, ...prev];
            return prev;
          });
        }
      } else {
        toast.error(data.detail || 'فشل تحميل القالب');
      }
    } catch (error) {
      toast.error('حدث خطأ في الاتصال');
    }
  }, [user]);

  const fetchUserCredits = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserCredits(data.credits || 0);
      }
    } catch (error) {
      console.error('Error fetching credits:', error);
    }
  };

  // Upload file to backend
  const handleFileUpload = useCallback(async (file, category = 'general') => {
    setIsUploading(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_category', category);
      
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/files/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      const data = await res.json();
      
      if (res.ok) {
        toast.success('تم رفع الملف بنجاح!');
        return data;
      } else {
        toast.error(data.detail || 'فشل رفع الملف');
        return null;
      }
    } catch (error) {
      toast.error('خطأ في رفع الملف');
      return null;
    } finally {
      setIsUploading(false);
    }
  }, []);
  
  // Handle file selection for chat
  const handleFileSelect = useCallback((file) => {
    setUploadedFile(file);
  }, []);
  
  // Send uploaded file as message
  const handleSendFile = useCallback(async () => {
    if (!uploadedFile || !currentSession) return;
    
    // Upload file first
    const uploadResult = await handleFileUpload(uploadedFile, 
      uploadedFile.type.startsWith('image/') ? 'reference' : 
      uploadedFile.type.startsWith('video/') ? 'reference' : 'document'
    );
    
    if (uploadResult) {
      // Send message with file reference
      const fileMessage = uploadedFile.type.startsWith('image/') 
        ? `[رفعت صورة: ${uploadedFile.name}]\nرابط الصورة: ${uploadResult.file_url}`
        : uploadedFile.type.startsWith('video/')
        ? `[رفعت فيديو مرجعي: ${uploadedFile.name}]\nرابط الفيديو: ${uploadResult.file_url}`
        : `[رفعت مستند: ${uploadedFile.name}]\nرابط الملف: ${uploadResult.file_url}`;
      
      setInputMessage(fileMessage);
      setUploadedFile(null);
      
      // Auto send
      setTimeout(() => {
        const sendBtn = document.querySelector('[data-testid="send-btn"]');
        if (sendBtn) sendBtn.click();
      }, 100);
    }
  }, [uploadedFile, currentSession, handleFileUpload]);
  
  // Open social export modal
  const openSocialExport = useCallback((asset) => {
    setExportAsset(asset);
    setShowSocialExport(true);
  }, []);

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const createSession = useCallback(async (type = 'general') => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_type: type })
      });
      const session = await res.json();
      setSessions(prev => [session, ...prev]);
      setCurrentSession(session);
      // Set messages from session (includes welcome message with buttons)
      setMessages(session.messages || []);
      setPreviewCode('');
      toast.success('تم إنشاء محادثة جديدة');
      if (window.innerWidth < 768) setSidebarOpen(false);
    } catch (error) {
      toast.error('فشل إنشاء المحادثة');
    }
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const session = await res.json();
      setCurrentSession(session);
      setMessages(session.messages || []);
      setPreviewCode('');
      if (window.innerWidth < 768) setSidebarOpen(false);
    } catch (error) {
      toast.error('فشل تحميل المحادثة');
    }
  }, []);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !currentSession || loading) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setLoading(true);
    setIsTyping(true);

    const tempUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      attachments: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${currentSession.id}/messages`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage, settings: { tts: ttsSettings, ultra: ultraMode } })
        }
      );

      const data = await res.json();

      if (res.ok) {
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id);
          return [...filtered, data.user_message, data.assistant_message];
        });
        
        if (data.credits_used) setUserCredits(prev => Math.max(0, prev - data.credits_used));
        if (ttsSettings.enabled && data.assistant_message?.audio_url) {
          playAudio(data.assistant_message.audio_url, data.assistant_message.id);
        }

        // Auto-open Live Preview when code is generated
        const metadata = data.assistant_message?.metadata || {};
        if (metadata.generated_code) {
          setPreviewCode(metadata.generated_code);
          setPreviewOpen(true);
        }

        if (sessions.find(s => s.id === currentSession.id)?.message_count === 0) {
          setSessions(prev => prev.map(s => 
            s.id === currentSession.id ? { ...s, title: userMessage.slice(0, 50), message_count: 2 } : s
          ));
        }
      } else {
        toast.error(data.detail || 'فشل إرسال الرسالة');
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      }
    } catch (error) {
      toast.error('حدث خطأ في الاتصال');
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  }, [inputMessage, currentSession, loading, ttsSettings, ultraMode, sessions]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!window.confirm('هل تريد حذف هذه المحادثة؟')) return;
    try {
      const token = localStorage.getItem('token');
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
        setPreviewCode('');
      }
      toast.success('تم حذف المحادثة');
    } catch (error) {
      toast.error('فشل حذف المحادثة');
    }
  }, [currentSession]);

  // Voice Recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await transcribeAudio(audioBlob);
      };
      recorder.start(100);
      setMediaRecorder(recorder);
      setIsRecording(true);
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000);
    } catch (error) {
      toast.error('فشل الوصول للمايكروفون');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      setIsRecording(false);
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  };

  const transcribeAudio = async (audioBlob) => {
    if (!currentSession) { toast.error('اختر محادثة أولاً'); return; }
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('language', 'ar');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/stt/transcribe`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        if (data.text?.trim()) {
          setInputMessage(data.text);
          toast.success('تم تحويل الصوت!');
        } else {
          toast.error('لم يتم التعرف على أي كلام');
        }
      }
    } catch (error) {
      toast.error('خطأ في تحويل الصوت');
    } finally {
      setLoading(false);
    }
  };

  const toggleRecording = () => { isRecording ? stopRecording() : startRecording(); };

  const playAudio = (audioUrl, messageId) => {
    if (playingAudio === messageId) {
      audioRef.current?.pause();
      setPlayingAudio(null);
    } else {
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        audioRef.current.play();
        setPlayingAudio(messageId);
        audioRef.current.onended = () => setPlayingAudio(null);
      }
    }
  };

  const generateTTS = async (text, messageId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/tts/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.replace(/```[\s\S]*?```/g, '').replace(/[*#_]/g, '').trim(),
          provider: ttsSettings.provider,
          voice: ttsSettings.voice,
          speed: ttsSettings.speed
        })
      });
      if (res.ok) {
        const data = await res.json();
        playAudio(data.audio_url, messageId);
        setMessages(prev => prev.map(m => m.id === messageId ? { ...m, audio_url: data.audio_url } : m));
      }
    } catch (error) {
      toast.error('فشل توليد الصوت');
    }
  };

  const downloadAsset = useCallback((url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const getSessionIcon = useCallback((type) => {
    switch (type) {
      case 'image': return <Image className="w-4 h-4" />;
      case 'video': return <Video className="w-4 h-4" />;
      case 'website': return <Globe className="w-4 h-4" />;
      case 'game': return <Gamepad2 className="w-4 h-4" />;
      case 'mobile': return <Smartphone className="w-4 h-4" />;
      default: return <MessageSquare className="w-4 h-4" />;
    }
  }, []);

  const handlePreview = useCallback((code) => {
    setPreviewCode(code);
    setPreviewOpen(true);
  }, []);

  // Handle button click from chat - send as message
  const handleButtonClick = useCallback((buttonText) => {
    if (loading || !currentSession) return;
    setInputMessage(buttonText);
    // Auto-send after a short delay
    setTimeout(() => {
      const input = document.querySelector('[data-testid="chat-input"]');
      if (input) {
        const event = new KeyboardEvent('keypress', { key: 'Enter', bubbles: true });
        // Directly call sendMessage with the button text
      }
    }, 100);
  }, [loading, currentSession]);
  
  // Effect to auto-send when inputMessage changes from button click
  const buttonClickRef = useRef(false);
  
  const handleButtonClickDirect = useCallback(async (buttonText) => {
    if (loading || !currentSession) return;
    
    setLoading(true);
    setIsTyping(true);

    const tempUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: buttonText,
      attachments: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/sessions/${currentSession.id}/messages`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: buttonText, settings: { tts: ttsSettings, ultra: ultraMode } })
        }
      );

      const data = await res.json();

      if (res.ok) {
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== tempUserMsg.id);
          return [...filtered, data.user_message, data.assistant_message];
        });
        
        if (data.credits_used) setUserCredits(prev => Math.max(0, prev - data.credits_used));

        // Auto-open Live Preview when code is generated
        const metadata = data.assistant_message?.metadata || {};
        if (metadata.generated_code) {
          setPreviewCode(metadata.generated_code);
          setPreviewOpen(true);
        }
      } else {
        toast.error(data.detail || 'فشل إرسال الرسالة');
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      }
    } catch (error) {
      toast.error('حدث خطأ في الاتصال');
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  }, [currentSession, loading, ttsSettings, ultraMode]);

  // Handle export code with credits deduction
  const handleExportCode = useCallback(async () => {
    if (!previewCode) {
      toast.error('لا يوجد كود للتصدير');
      return;
    }
    
    if (userCredits < 50 && user?.role !== 'owner') {
      toast.error('رصيد غير كافٍ! التصدير يكلف 50 نقطة');
      return;
    }
    
    // Remove Zitex badge for export
    let cleanCode = previewCode.replace(/<!-- Zitex Badge -->[\s\S]*?<\/div>/g, '');
    
    // Download as HTML file
    const blob = new Blob([cleanCode], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'zitex-project.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    // Deduct credits (TODO: call backend)
    if (user?.role !== 'owner') {
      setUserCredits(prev => Math.max(0, prev - 50));
    }
    
    toast.success('تم تصدير الكود بنجاح! (-50 نقطة)');
  }, [previewCode, userCredits, user]);

  // Handle save as template
  const handleSaveTemplate = useCallback(async (templateName) => {
    if (!currentSession) {
      toast.error('اختر محادثة أولاً');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/templates/save`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSession.id,
          name: templateName,
          category: currentSession.session_type || 'custom'
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        toast.success(data.message || 'تم حفظ القالب بنجاح!');
        if (user?.role !== 'owner') {
          setUserCredits(prev => Math.max(0, prev - 10));
        }
      } else {
        toast.error(data.detail || 'فشل حفظ القالب');
      }
    } catch (error) {
      toast.error('حدث خطأ في الاتصال');
    }
  }, [currentSession, user]);

  // Handle deploy
  const handleDeploy = useCallback(async (subdomain) => {
    if (!currentSession) {
      toast.error('اختر محادثة أولاً');
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/chat/deploy`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSession.id,
          subdomain: subdomain
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        toast.success(`🚀 تم النشر بنجاح!\n${data.url}`);
        if (user?.role !== 'owner') {
          setUserCredits(prev => Math.max(0, prev - 100));
        }
        // Update current session with deployment info
        setCurrentSession(prev => ({
          ...prev,
          deployment: {
            id: data.id,
            subdomain: subdomain,
            url: data.url,
            status: 'active'
          }
        }));
      } else {
        toast.error(data.detail || 'فشل النشر');
      }
    } catch (error) {
      toast.error('حدث خطأ في الاتصال');
    }
  }, [currentSession, user]);

  const renderAttachment = useCallback((attachment, onPreview) => {
    switch (attachment.type) {
      case 'image':
      case 'image_preview':
        return (
          <div className="mt-3 relative group rounded-xl overflow-hidden">
            <img src={attachment.url} alt={attachment.prompt || "Generated"} className="max-w-full rounded-xl" loading="lazy" />
            {attachment.scene && (
              <div className="absolute top-2 left-2 bg-black/70 px-2 py-1 rounded-lg text-xs text-white">
                مشهد {attachment.scene}
              </div>
            )}
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <Button size="sm" onClick={() => downloadAsset(attachment.url, 'zitex-image.png')} className="bg-white/20 backdrop-blur">
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    const token = localStorage.getItem('token');
                    const res = await fetch(`${API_URL}/api/user-images`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                      body: JSON.stringify({ url: attachment.url, prompt: attachment.prompt || '', source_session_id: currentSession?.id || null }),
                    });
                    if (res.ok) {
                      toast.success('✅ حُفظت الصورة في المحرر — افتح "المحرر المرئي" لاستخراج عناصر منها', { duration: 5000 });
                    } else {
                      const t = await res.text();
                      toast.error('فشل الحفظ: ' + t);
                    }
                  } catch (e) { toast.error('فشل الاتصال: ' + e.message); }
                }}
                className="bg-yellow-500 backdrop-blur hover:bg-yellow-400 text-black font-bold"
                data-testid={`save-img-to-designer-${attachment.id || 'x'}`}
                title="احفظ الصورة في مكتبة المحرر لاستخراج عناصر منها لاحقاً"
              >
                ✂️ حفظ للمحرر
              </Button>
              <Button size="sm" onClick={() => openSocialExport({ id: attachment.id || 'temp', url: attachment.url, type: 'image' })} className="bg-purple-500/80 backdrop-blur hover:bg-purple-500">
                <Share2 className="w-4 h-4 me-1" /> نشر
              </Button>
            </div>
          </div>
        );
      case 'video':
        return (
          <div className="mt-3 bg-slate-800/50 rounded-xl p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Video className="w-5 h-5 text-orange-400" />
              <span className="text-white font-medium text-sm">
                {attachment.video_type === 'cinematic' ? 'فيديو سينمائي' : 
                 attachment.video_type === 'funny' ? 'فيديو مضحك' : 
                 attachment.video_type === 'advertising' ? 'فيديو إعلاني' : 'فيديو'}
              </span>
              {attachment.duration && (
                <span className="text-xs text-gray-400">({attachment.duration} ثواني)</span>
              )}
            </div>
            <video src={attachment.url} controls className="w-full rounded-xl" preload="metadata" />
            <div className="flex gap-2 mt-2">
              <Button size="sm" onClick={() => downloadAsset(attachment.url, 'zitex-video.mp4')} className="bg-orange-500 hover:bg-orange-600">
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
              <Button size="sm" onClick={() => openSocialExport({ id: attachment.id || 'temp', url: attachment.url, type: 'video' })} className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600">
                <Share2 className="w-4 h-4 me-1" /> نشر للمنصات
              </Button>
            </div>
          </div>
        );
      case 'audio':
      case 'audio_preview':
        return (
          <div className="mt-3 bg-purple-500/10 border border-purple-500/30 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-2">
              <Volume2 className="w-5 h-5 text-purple-400" />
              <span className="text-purple-300 font-medium text-sm">
                {attachment.type === 'audio_preview' ? 'معاينة التعليق الصوتي' : 'التعليق الصوتي'}
              </span>
              {attachment.voice && (
                <span className="text-xs text-purple-400/60">({attachment.voice})</span>
              )}
            </div>
            <audio src={attachment.url} controls className="w-full" />
            {attachment.text && (
              <p className="text-xs text-gray-400 mt-2 italic">"{attachment.text.slice(0, 100)}..."</p>
            )}
          </div>
        );
      case 'website':
      case 'game':
        return (
          <div className="mt-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              {attachment.type === 'game' ? <Gamepad2 className="w-5 h-5 text-cyan-400" /> : <Globe className="w-5 h-5 text-green-400" />}
              <span className="text-white font-medium text-sm">{attachment.type === 'game' ? 'لعبة جاهزة!' : 'موقع جاهز!'}</span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => onPreview(attachment.code || Object.values(attachment.files || {})[0])} className="bg-green-500 hover:bg-green-600">
                <Eye className="w-4 h-4 me-1" /> معاينة
              </Button>
              <Button size="sm" variant="outline" onClick={() => downloadAsset(URL.createObjectURL(new Blob([attachment.code], { type: 'text/html' })), `zitex-${attachment.type}.html`)}>
                <Download className="w-4 h-4 me-1" /> تحميل
              </Button>
            </div>
          </div>
        );
      case 'video_pending':
        return (
          <div className="mt-3 p-3 bg-orange-500/10 border border-orange-500/20 rounded-xl flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-orange-400 animate-spin" />
            <span className="text-orange-300 text-sm">جاري توليد الفيديو...</span>
          </div>
        );
      default:
        return null;
    }
  }, [downloadAsset]);

  return (
    <div className="h-screen bg-[#0a0a12] flex flex-col overflow-hidden" data-testid="ai-chat-page">
      <Navbar user={user} transparent />
      <audio ref={audioRef} className="hidden" />
      
      <div className="flex-1 flex mt-16 overflow-hidden">
        {/* Sessions Dropdown Button - Always visible */}
        <div className="fixed top-20 right-4 z-30 flex items-center gap-2">
          <button
            onClick={() => (window.location.href = '/designer')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl shadow-lg border border-yellow-500/40 bg-gradient-to-r from-yellow-600/30 to-orange-600/30 text-yellow-300 hover:from-yellow-600/50 hover:to-orange-600/50 transition-all"
            data-testid="open-designer-btn"
            title="المحرر المرئي"
          >
            <span className="text-base">🎨</span>
            <span className="text-sm font-medium">المحرر المرئي</span>
          </button>
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)} 
            className={`flex items-center gap-2 px-4 py-2 rounded-xl shadow-lg border transition-all ${sidebarOpen ? 'bg-amber-600 border-amber-500 text-white' : 'bg-slate-800 border-slate-700 text-white hover:bg-slate-700'}`}
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm font-medium">المحادثات</span>
            <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full">{sessions.length}</span>
          </button>
          
          {/* Dropdown Panel */}
          {sidebarOpen && (
            <div className="absolute top-12 right-0 w-80 bg-[#0d0d18] border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden animate-fadeIn">
              {/* User Credits Header */}
              <div className="p-3 border-b border-slate-800/50 bg-gradient-to-r from-slate-800/50 to-slate-900/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center">
                      <span className="text-black text-sm font-bold">{user?.email?.[0]?.toUpperCase() || 'U'}</span>
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium">{user?.role === 'owner' ? 'مالك' : 'مستخدم'}</p>
                      <p className="text-xs text-amber-400 flex items-center gap-1">
                        <Coins className="w-3 h-3" />
                        <span className="font-bold">{user?.role === 'owner' ? '∞' : userCredits}</span> نقطة
                      </p>
                    </div>
                  </div>
                  <button onClick={() => setSidebarOpen(false)} className="p-2 rounded-lg hover:bg-slate-700/50 text-gray-400">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* New Chat Button */}
              <div className="p-3 border-b border-slate-800/50">
                <Button onClick={() => { createSession('general'); setSidebarOpen(false); }} className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 shadow-lg shadow-amber-500/20" data-testid="new-chat-btn">
                  <Plus className="w-4 h-4 me-2" /> محادثة جديدة
                </Button>
                <div className="grid grid-cols-5 gap-1.5 mt-2">
                  {[
                    { type: 'image', icon: Image, color: 'purple', label: 'صورة' },
                    { type: 'video', icon: Video, color: 'orange', label: 'فيديو' },
                    { type: 'mobile', icon: Smartphone, color: 'pink', label: 'تطبيق' },
                    { type: 'website', icon: Globe, color: 'green', label: 'موقع' },
                    { type: 'game', icon: Gamepad2, color: 'cyan', label: 'لعبة' }
                  ].map(({ type, icon: Icon, color, label }) => (
                    <button 
                      key={type} 
                      onClick={() => { createSession(type); setSidebarOpen(false); }} 
                      className={`p-2 rounded-lg border border-${color}-500/30 bg-${color}-500/10 hover:bg-${color}-500/20 transition-all flex flex-col items-center gap-1`}
                      title={label}
                    >
                      <Icon className={`w-4 h-4 text-${color}-400`} />
                      <span className={`text-[10px] text-${color}-400`}>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Sessions List */}
              <div className="max-h-80 overflow-y-auto">
                {sessionsLoading ? <SessionSkeleton /> : sessions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Sparkles className="w-10 h-10 mx-auto mb-2 opacity-20" />
                    <p className="text-sm">لا توجد محادثات سابقة</p>
                    <p className="text-xs text-gray-600">ابدأ محادثة جديدة!</p>
                  </div>
                ) : (
                  <div className="p-2 space-y-1">
                    <p className="text-xs text-gray-500 px-2 py-1">المحادثات السابقة ({sessions.length})</p>
                    {sessions.map(session => (
                      <div key={session.id} onClick={() => { loadSession(session.id); setSidebarOpen(false); }}>
                        <SessionItem session={session} isActive={currentSession?.id === session.id} onSelect={() => {}} onDelete={deleteSession} getIcon={getSessionIcon} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Overlay when dropdown is open */}
        {sidebarOpen && <div className="fixed inset-0 z-20" onClick={() => setSidebarOpen(false)} />}

        {/* Main Area - Full Width */}
        <div className={`flex-1 flex ${previewOpen ? 'flex-row' : 'flex-col'} overflow-hidden w-full`}>
          {/* Chat Column */}
          <div className={`${previewOpen ? 'w-1/2 border-l border-slate-800/50' : 'w-full'} flex flex-col overflow-hidden`}>
            {!currentSession ? (
              /* Welcome Screen — Premium Hero + 6 Cards + Standalone Studio CTA */
              <div className="flex-1 overflow-y-auto">
                <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12">
                  <div className="text-center mb-8 sm:mb-10">
                    <ZitexLogo size="xl" isAnimating={false} />
                    <h1 className="text-3xl sm:text-4xl font-black text-white mt-5 mb-2">
                      مرحباً بك في <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-500">Zitex</span>
                    </h1>
                    <p className="text-amber-200/80 text-sm sm:text-base">مساعدك الذكي لإنشاء المواقع والصور والفيديوهات والتطبيقات</p>
                  </div>

                  {/* 🆕 STANDALONE FEATURED CTA — Build website from scratch */}
                  <div
                    onClick={() => (window.location.href = '/websites')}
                    className="relative mb-8 cursor-pointer group rounded-2xl overflow-hidden border border-amber-400/30 hover:border-amber-300/60 transition-all hover:shadow-[0_20px_60px_-12px_rgba(245,158,11,0.5)]"
                    data-testid="hero-build-website-from-scratch"
                  >
                    <div
                      className="absolute inset-0 bg-cover bg-center scale-105 group-hover:scale-110 transition-transform duration-700"
                      style={{
                        backgroundImage: `url('https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1600&q=70')`,
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-l from-black/95 via-black/70 to-amber-900/40" />
                    <div className="relative p-5 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center gap-5">
                      <div className="flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/40">
                        <Sparkles className="w-9 h-9 sm:w-11 sm:h-11 text-black" />
                      </div>
                      <div className="flex-1 text-right">
                        <div className="inline-block px-2 py-0.5 rounded-md bg-amber-400/20 border border-amber-300/40 text-amber-300 text-[10px] font-black tracking-wider mb-2">
                          الأكثر طلباً
                        </div>
                        <h2 className="text-2xl sm:text-3xl font-black text-white mb-1">
                          أنشئ موقعك من الصفر <span className="text-amber-300">بمحادثة ذكية</span>
                        </h2>
                        <p className="text-white/75 text-xs sm:text-sm leading-relaxed">
                          استوديو احترافي بـ ٢٥ تخصص — تحكّم عميق بالألوان والأشكال والأزرار والـ widgets، مع تصميم مخصص بالذكاء الاصطناعي
                        </p>
                      </div>
                      <div className="flex-shrink-0">
                        <div className="px-5 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 text-black font-black text-sm whitespace-nowrap shadow-lg group-hover:scale-105 transition-transform">
                          ابدأ الآن →
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 6 Creative Cards Grid */}
                  <div className="text-center mb-5">
                    <div className="text-xs font-bold text-amber-300/70 tracking-widest mb-1">أو اختر الإنشاء السريع</div>
                    <div className="h-px w-20 mx-auto bg-gradient-to-r from-transparent via-amber-400/40 to-transparent"></div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
                    {[
                      {
                        type: 'website-template',
                        title: 'مواقع جاهزة',
                        desc: '٢٥ قالب جاهز',
                        gradient: 'from-emerald-500/20 to-teal-500/10',
                        accent: '#10b981',
                        bgImage: 'https://images.unsplash.com/photo-1467232004584-a241de8bcf5d?auto=format&fit=crop&w=800&q=70',
                        action: () => (window.location.href = '/websites'),
                      },
                      {
                        type: 'mobile',
                        title: 'تطبيق موبايل',
                        desc: 'Flutter / Swift / Kotlin',
                        gradient: 'from-pink-500/20 to-rose-500/10',
                        accent: '#ec4899',
                        bgImage: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=800&q=70',
                        action: () => createSession('mobile'),
                      },
                      {
                        type: 'web-to-app',
                        title: 'تحويل موقع لتطبيق',
                        desc: 'Web → Android/iOS',
                        gradient: 'from-cyan-500/20 to-sky-500/10',
                        accent: '#06b6d4',
                        bgImage: 'https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?auto=format&fit=crop&w=800&q=70',
                        action: () => createSession('mobile'),
                      },
                      {
                        type: 'game',
                        title: 'إنشاء الألعاب',
                        desc: 'Phaser / Three.js',
                        gradient: 'from-cyan-500/20 to-blue-500/10',
                        accent: '#0ea5e9',
                        bgImage: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=70',
                        action: () => createSession('game'),
                      },
                      {
                        type: 'image',
                        title: 'إنشاء الصور',
                        desc: 'GPT Image 1 / Nano Banana',
                        gradient: 'from-purple-500/20 to-violet-500/10',
                        accent: '#a855f7',
                        bgImage: 'https://images.unsplash.com/photo-1561735445-df9c3deef91d?auto=format&fit=crop&w=800&q=70',
                        action: () => createSession('image'),
                      },
                      {
                        type: 'video',
                        title: 'إنشاء الفيديوهات',
                        desc: 'Sora 2',
                        gradient: 'from-orange-500/20 to-red-500/10',
                        accent: '#f97316',
                        bgImage: 'https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=800&q=70',
                        action: () => createSession('video'),
                      },
                    ].map(({ type, title, desc, gradient, accent, bgImage, action }) => (
                      <div
                        key={type}
                        onClick={action}
                        className="relative group cursor-pointer rounded-xl overflow-hidden aspect-[4/3] sm:aspect-[5/4] border border-white/10 hover:border-white/30 transition-all hover:scale-[1.03] hover:shadow-2xl"
                        style={{ boxShadow: `0 0 0 0 ${accent}` }}
                        onMouseEnter={(e) => (e.currentTarget.style.boxShadow = `0 12px 40px -8px ${accent}80`)}
                        onMouseLeave={(e) => (e.currentTarget.style.boxShadow = '')}
                        data-testid={`hero-card-${type}`}
                      >
                        {/* Background image */}
                        <div
                          className="absolute inset-0 bg-cover bg-center scale-110 group-hover:scale-125 transition-transform duration-700"
                          style={{ backgroundImage: `url('${bgImage}')` }}
                        />
                        {/* Color overlay */}
                        <div className={`absolute inset-0 bg-gradient-to-tr ${gradient}`} />
                        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-black/20" />
                        {/* Content */}
                        <div className="relative h-full flex flex-col justify-end p-3 sm:p-4 text-right">
                          <h3 className="text-white font-black text-base sm:text-lg mb-0.5" style={{ textShadow: '0 2px 8px rgba(0,0,0,.5)' }}>
                            {title}
                          </h3>
                          <p className="text-[10px] sm:text-xs text-white/75 font-medium">{desc}</p>
                        </div>
                        {/* Top-right accent corner */}
                        <div className="absolute top-2 right-2 w-2 h-2 rounded-full" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
                      </div>
                    ))}
                  </div>

                  <div className="mt-7 flex justify-center">
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={() => setShowTemplatesPanel(true)}
                      className="border-purple-500/40 text-purple-300 hover:bg-purple-500/10"
                      data-testid="hero-browse-templates"
                    >
                      <Layout className="w-4 h-4 me-2" /> تصفّح القوالب الجاهزة
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* Messages */}
                <ScrollArea className="flex-1 p-4">
                  <div className="max-w-3xl mx-auto space-y-4">
                    {messages.length === 0 && (
                      <div className="text-center py-16 text-gray-500">
                        <Bot className="w-16 h-16 mx-auto mb-4 opacity-20" />
                        <p>ابدأ المحادثة!</p>
                      </div>
                    )}
                    {messages.map((msg, idx) => (
                      <ChatMessage key={msg.id || idx} msg={msg} idx={idx} renderAttachment={renderAttachment} onPlayAudio={playAudio} onGenerateTTS={generateTTS} playingAudio={playingAudio} onPreview={handlePreview} isTyping={isTyping && idx === messages.length - 1 && msg.role === 'assistant'} onButtonClick={handleButtonClickDirect} />
                    ))}
                    {isTyping && (
                      <div className="flex justify-end">
                        <div className="flex items-start gap-3">
                          <div className="bg-slate-800 rounded-2xl rounded-tr-md p-4 border border-slate-700/50">
                            <div className="flex items-center gap-2">
                              {[0, 1, 2].map(i => <span key={i} className="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />)}
                              <span className="text-gray-400 text-sm mr-2">جاري التفكير...</span>
                            </div>
                          </div>
                          <ZitexLogo size="sm" isAnimating={true} />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>

                {/* Input Area */}
                <div className="border-t border-slate-800/50 p-3 bg-[#0d0d18]/90 backdrop-blur">
                  <div className="max-w-3xl mx-auto">
                    {/* Credits Banner */}
                    <CreditsBanner credits={userCredits} isOwner={user?.role === 'owner'} onBuyCredits={() => toast.info('سيتم إضافة هذه الميزة قريباً')} />
                    
                    {/* Input Box */}
                    <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden focus-within:border-purple-500/50 transition-colors">
                      {/* Recording Indicator */}
                      {isRecording && (
                        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 flex items-center gap-3">
                          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                          <span className="text-red-400 text-sm font-mono">
                            {Math.floor(recordingTime / 60).toString().padStart(2, '0')}:{(recordingTime % 60).toString().padStart(2, '0')}
                          </span>
                          <span className="text-red-300/70 text-xs">جاري التسجيل...</span>
                        </div>
                      )}
                      
                      {/* Text Area */}
                      <textarea
                        ref={textareaRef}
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Message Agent"
                        className="w-full bg-transparent text-white placeholder:text-gray-500 text-sm resize-none focus:outline-none min-h-[50px] max-h-[150px] p-4"
                        disabled={loading}
                        rows={1}
                        data-testid="chat-input"
                      />
                      
                      {/* Bottom Tools */}
                      <div className="flex items-center justify-between px-3 py-2 border-t border-slate-700/30">
                        <div className="flex items-center gap-1">
                          {/* Attach File - NOW ACTIVE! */}
                          <FileUploadButton onFileSelect={handleFileSelect} />
                          
                          {/* Save Template */}
                          <button 
                            onClick={() => setShowTemplatesPanel(true)}
                            className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-400 hover:text-amber-400 hover:bg-amber-500/10 transition-all text-xs" 
                            title="القوالب"
                          >
                            <Save className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">قوالب</span>
                          </button>
                          
                          {/* Social Export */}
                          <button 
                            onClick={() => setShowSocialExport(true)}
                            className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 transition-all text-xs" 
                            title="نشر للمنصات"
                          >
                            <Share2 className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">نشر</span>
                          </button>
                          
                          {/* Ultra Mode */}
                          <button 
                            onClick={() => setUltraMode(!ultraMode)}
                            className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition-all ${ultraMode ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-gray-500 hover:text-gray-400 hover:bg-slate-700/50'}`}
                            title="وضع Ultra"
                          >
                            <Zap className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Ultra</span>
                            <div className={`w-6 h-3.5 rounded-full transition-colors ${ultraMode ? 'bg-amber-500' : 'bg-slate-600'}`}>
                              <div className={`w-2.5 h-2.5 rounded-full bg-white transition-transform mt-0.5 ${ultraMode ? 'translate-x-3' : 'translate-x-0.5'}`} />
                            </div>
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-1">
                          {/* Mic */}
                          <button
                            onClick={toggleRecording}
                            disabled={loading}
                            className={`p-2 rounded-lg transition-all ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'text-gray-400 hover:text-white hover:bg-slate-700/50'}`}
                          >
                            <Mic className="w-5 h-5" />
                          </button>
                          
                          {/* Send */}
                          <button
                            onClick={sendMessage}
                            disabled={loading || !inputMessage.trim() || isRecording}
                            className="p-2 rounded-lg bg-gradient-to-r from-amber-600 to-yellow-600 text-white disabled:opacity-50 hover:from-amber-700 hover:to-yellow-700 transition-all shadow-lg shadow-amber-500/20"
                            data-testid="send-btn"
                          >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          
          {/* Preview Panel */}
          {previewOpen && (
            <div className={`${previewFullscreen ? 'fixed inset-0 z-50' : 'w-1/2'}`}>
              <LivePreviewPanel 
                code={previewCode} 
                isOpen={previewOpen} 
                onClose={() => setPreviewOpen(false)} 
                onRefresh={() => {
                  if (previewCode) {
                    const temp = previewCode;
                    setPreviewCode('');
                    setTimeout(() => setPreviewCode(temp), 100);
                  }
                }} 
                isFullscreen={previewFullscreen} 
                onToggleFullscreen={() => setPreviewFullscreen(!previewFullscreen)}
                onExportCode={handleExportCode}
                userCredits={userCredits}
                onSaveTemplate={handleSaveTemplate}
                onDeploy={handleDeploy}
                currentSession={currentSession}
              />
            </div>
          )}
        </div>
      </div>
      
      {/* Styles */}
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin-slow { animation: spin-slow 2s linear infinite; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
      `}</style>
      
      {/* Templates Panel */}
      {showTemplatesPanel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-4xl mx-4 max-h-[85vh] overflow-hidden flex flex-col animate-fadeIn">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Layout className="w-7 h-7 text-purple-400" />
                القوالب الجاهزة
              </h2>
              <button onClick={() => setShowTemplatesPanel(false)} className="p-2 rounded-lg hover:bg-slate-800 text-gray-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
              {['الكل', 'landing', 'ecommerce', 'portfolio', 'dashboard', 'game', 'custom'].map(cat => (
                <button 
                  key={cat} 
                  className="px-4 py-2 rounded-full text-sm whitespace-nowrap bg-slate-800 hover:bg-slate-700 text-gray-300 border border-slate-700"
                >
                  {cat === 'الكل' ? cat : cat === 'landing' ? 'صفحات هبوط' : cat === 'ecommerce' ? 'متاجر' : cat === 'portfolio' ? 'معارض' : cat === 'dashboard' ? 'لوحات تحكم' : cat === 'game' ? '🎮 ألعاب' : 'مخصص'}
                </button>
              ))}
            </div>
            
            <div className="flex-1 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {templates.map(template => (
                  <div 
                    key={template.id} 
                    className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden hover:border-purple-500/50 transition-all group"
                  >
                    <div className="h-40 bg-gradient-to-br from-purple-500/20 to-pink-500/20 relative overflow-hidden flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-5xl mb-2">
                          {template.category === 'ecommerce' ? '🛒' : template.category === 'dashboard' ? '📊' : template.category === 'portfolio' ? '👤' : template.category === 'game' ? '🎮' : template.category === 'landing' ? '🌐' : '✨'}
                        </div>
                        <div className="text-xs text-gray-400 bg-black/30 px-2 py-1 rounded">
                          {template.category === 'game' ? (template.id.includes('3d') ? 'Three.js' : 'Phaser.js') : 'Tailwind CSS'}
                        </div>
                      </div>
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button
                          onClick={() => handleUseTemplate(template.id)}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-white text-sm font-medium"
                        >
                          استخدام القالب
                        </button>
                      </div>
                      {template.is_premium && (
                        <span className="absolute top-2 left-2 px-2 py-1 bg-amber-500 text-black text-xs font-bold rounded-full">Premium</span>
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="text-white font-medium mb-1">{template.name}</h3>
                      <p className="text-gray-400 text-sm mb-2 line-clamp-2">{template.description}</p>
                      <div className="flex items-center justify-between">
                        <span className={`text-xs px-2 py-1 rounded-full ${template.cost > 0 ? 'bg-amber-500/20 text-amber-400' : 'bg-green-500/20 text-green-400'}`}>
                          {template.cost > 0 ? `${template.cost} نقطة` : 'مجاني'}
                        </span>
                        {template.uses_count > 0 && (
                          <span className="text-xs text-gray-500">{template.uses_count} استخدام</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {templates.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  <Layout className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>لا توجد قوالب متاحة</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Uploaded File Preview */}
      {uploadedFile && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 w-full max-w-lg">
          <UploadedFilePreview 
            file={uploadedFile} 
            onRemove={() => setUploadedFile(null)} 
            onSend={handleSendFile}
          />
        </div>
      )}
      
      {/* Social Export Modal */}
      <SocialExportModal
        isOpen={showSocialExport}
        onClose={() => { setShowSocialExport(false); setExportAsset(null); }}
        assetId={exportAsset?.id}
        assetUrl={exportAsset?.url}
        assetType={exportAsset?.type}
      />
    </div>
  );
};

export default AIChat;
