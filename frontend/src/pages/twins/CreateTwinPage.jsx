/**
 * Create Digital Twin Page
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { 
  Upload, 
  Mic, 
  Camera, 
  User, 
  Sparkles,
  AlertCircle,
  Check,
  X,
  Loader2
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useAuth } from '../../contexts/AuthContext';
import { TwinService } from '../../services/api/twinService';
import { StepIndicator } from '../../components/StepIndicator';
import { VoiceRecorder } from '../../components/VoiceRecorder';
import { ImageUploader } from '../../components/ImageUploader';
import { PersonalityBuilder } from '../../components/PersonalityBuilder';

export default function CreateTwinPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    voiceSample: null,
    faceImages: [],
    personalityTraits: {
      communication_style: 'friendly',
      formality_level: 'medium',
      humor_level: 5,
      empathy_level: 7,
      creativity_level: 6,
      detail_oriented: 8,
    },
    additionalInfo: ''
  });

  // Create twin mutation
  const createTwinMutation = useMutation({
    mutationFn: TwinService.createDigitalTwin,
    onSuccess: (data) => {
      toast.success(t('twin_creation_started'));
      queryClient.invalidateQueries(['digital-twins']);
      navigate(`/app/twins/${data.id}`);
    },
    onError: (error) => {
      toast.error(error.message || t('creation_failed'));
      setError(error.message);
    }
  });

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError(t('name_required'));
      return;
    }
    
    if (!formData.voiceSample) {
      setError(t('voice_sample_required'));
      return;
    }
    
    if (formData.faceImages.length < 3) {
      setError(t('min_images_required'));
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('voice_sample', formData.voiceSample);
      
      formData.faceImages.forEach((image, index) => {
        formDataToSend.append(`face_images`, image);
      });
      
      if (formData.additionalInfo) {
        formDataToSend.append('personality_traits', JSON.stringify({
          ...formData.personalityTraits,
          additional_info: formData.additionalInfo
        }));
      } else {
        formDataToSend.append('personality_traits', JSON.stringify(formData.personalityTraits));
      }
      
      await createTwinMutation.mutateAsync(formDataToSend);
      
    } catch (err) {
      console.error('Creation error:', err);
      setError(err.message || t('creation_failed'));
    } finally {
      setLoading(false);
    }
  };

  // Step handlers
  const nextStep = () => {
    if (step < 4) {
      setStep(step + 1);
      setError('');
    }
  };

  const prevStep = () => {
    if (step > 1) {
      setStep(step - 1);
      setError('');
    }
  };

  // Update form data
  const updateFormData = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Steps configuration
  const steps = [
    { number: 1, title: t('step_basic_info'), icon: User },
    { number: 2, title: t('step_voice_sample'), icon: Mic },
    { number: 3, title: t('step_face_images'), icon: Camera },
    { number: 4, title: t('step_personality'), icon: Sparkles },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          {t('create_digital_twin')}
        </h1>
        <p className="text-gray-400 mt-2">
          {t('create_twin_description')}
        </p>
      </div>

      {/* Step Indicator */}
      <StepIndicator steps={steps} currentStep={step} />

      {/* Error Alert */}
      {error && (
        <div className="mt-6 p-4 bg-red-500 bg-opacity-10 border border-red-500 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="text-red-300 text-sm">{error}</div>
          <button 
            onClick={() => setError('')}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="mt-8">
        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('twin_name')} *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => updateFormData('name', e.target.value)}
                placeholder={t('twin_name_placeholder')}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                required
              />
              <p className="mt-2 text-sm text-gray-400">
                {t('twin_name_helper')}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('additional_info')}
              </label>
              <textarea
                value={formData.additionalInfo}
                onChange={(e) => updateFormData('additionalInfo', e.target.value)}
                placeholder={t('additional_info_placeholder')}
                rows={4}
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="mt-2 text-sm text-gray-400">
                {t('additional_info_helper')}
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Voice Sample */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-300 mb-4">
                {t('record_voice_sample')}
              </h3>
              <p className="text-gray-400 mb-6">
                {t('voice_sample_instructions')}
              </p>
              
              <VoiceRecorder
                onRecordingComplete={(audioBlob) => {
                  const file = new File([audioBlob], 'voice_sample.wav', { type: 'audio/wav' });
                  updateFormData('voiceSample', file);
                }}
                maxDuration={30}
              />
              
              {formData.voiceSample && (
                <div className="mt-6 p-4 bg-green-500 bg-opacity-10 border border-green-500 rounded-lg flex items-center space-x-3">
                  <Check className="w-5 h-5 text-green-400" />
                  <div className="text-green-300">
                    {t('voice_sample_recorded')}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-lg p-6">
              <h4 className="font-medium text-gray-300 mb-3">
                {t('voice_tips_title')}
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('voice_tip_1')}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('voice_tip_2')}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('voice_tip_3')}</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Step 3: Face Images */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-300 mb-4">
                {t('upload_face_images')}
              </h3>
              <p className="text-gray-400 mb-6">
                {t('face_images_instructions')}
              </p>
              
              <ImageUploader
                onImagesUploaded={(images) => updateFormData('faceImages', images)}
                maxImages={10}
                minImages={3}
                accept="image/*"
              />
              
              {formData.faceImages.length > 0 && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-medium text-gray-300">
                      {t('uploaded_images')} ({formData.faceImages.length})
                    </div>
                    <button
                      type="button"
                      onClick={() => updateFormData('faceImages', [])}
                      className="text-sm text-red-400 hover:text-red-300"
                    >
                      {t('clear_all')}
                    </button>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                    {formData.faceImages.map((image, index) => (
                      <div key={index} className="relative group">
                        <img
                          src={URL.createObjectURL(image)}
                          alt={`Face ${index + 1}`}
                          className="w-full h-32 object-cover rounded-lg"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const newImages = [...formData.faceImages];
                            newImages.splice(index, 1);
                            updateFormData('faceImages', newImages);
                          }}
                          className="absolute top-2 right-2 p-1 bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-lg p-6">
              <h4 className="font-medium text-gray-300 mb-3">
                {t('face_tips_title')}
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('face_tip_1')}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('face_tip_2')}</span>
                </li>
                <li className="flex items-start space-x-2">
                  <Check className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                  <span>{t('face_tip_3')}</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* Step 4: Personality */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-300 mb-4">
                {t('define_personality')}
              </h3>
              <p className="text-gray-400 mb-6">
                {t('personality_instructions')}
              </p>
              
              <PersonalityBuilder
                traits={formData.personalityTraits}
                onTraitsChange={(traits) => updateFormData('personalityTraits', traits)}
              />
            </div>

            <div className="bg-gray-800 rounded-lg p-6">
              <h4 className="font-medium text-gray-300 mb-3">
                {t('personality_preview')}
              </h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-400">{t('communication_style')}</div>
                  <div className="px-3 py-1 bg-purple-500 bg-opacity-20 text-purple-300 rounded-full text-sm">
                    {formData.personalityTraits.communication_style}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-400">{t('humor_level')}</div>
                  <div className="flex items-center space-x-2">
                    {[...Array(10)].map((_, i) => (
                      <div
                        key={i}
                        className={cn(
                          "w-2 h-6 rounded-sm",
                          i < formData.personalityTraits.humor_level
                            ? "bg-yellow-500"
                            : "bg-gray-600"
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="mt-8 flex justify-between">
          <div>
            {step > 1 && (
              <button
                type="button"
                onClick={prevStep}
                className="px-6 py-3 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
                disabled={loading}
              >
                {t('previous')}
              </button>
            )}
          </div>
          
          <div className="flex space-x-4">
            {step < 4 ? (
              <button
                type="button"
                onClick={nextStep}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:opacity-90 transition-opacity"
                disabled={loading}
              >
                {t('next')}
              </button>
            ) : (
              <button
                type="submit"
                disabled={loading || !formData.name || !formData.voiceSample || formData.faceImages.length < 3}
                className={cn(
                  "px-6 py-3 bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-lg transition-all",
                  loading || !formData.name || !formData.voiceSample || formData.faceImages.length < 3
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:opacity-90"
                )}
              >
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>{t('creating_twin')}</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <Sparkles className="w-5 h-5" />
                    <span>{t('create_twin')}</span>
                  </div>
                )}
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Progress Info */}
      <div className="mt-12">
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-medium text-gray-300 mb-4">
            {t('what_happens_next')}
          </h3>
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-full bg-purple-500 bg-opacity-20 flex items-center justify-center flex-shrink-0">
                <Mic className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <div className="font-medium text-gray-300">{t('voice_training')}</div>
                <div className="text-sm text-gray-400">{t('voice_training_description')}</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-full bg-pink-500 bg-opacity-20 flex items-center justify-center flex-shrink-0">
                <Camera className="w-4 h-4 text-pink-400" />
              </div>
              <div>
                <div className="font-medium text-gray-300">{t('face_training')}</div>
                <div className="text-sm text-gray-400">{t('face_training_description')}</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-full bg-blue-500 bg-opacity-20 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-blue-400" />
              </div>
              <div>
                <div className="font-medium text-gray-300">{t('personality_training')}</div>
                <div className="text-sm text-gray-400">{t('personality_training_description')}</div>
              </div>
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-gray-700">
            <div className="text-sm text-gray-400">
              <strong>{t('note')}:</strong> {t('creation_time_note')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}