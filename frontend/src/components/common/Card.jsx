const Card = ({
  children,
  title,
  subtitle,
  headerAction,
  className = '',
  padding = true,
  hover = false
}) => {
  return (
    <div className={`bg-white rounded-lg shadow-md ${hover ? 'hover:shadow-lg transition-shadow duration-200' : ''} ${className}`}>
      {(title || headerAction) && (
        <div className={`border-b border-gray-200 ${padding ? 'px-6 py-4' : 'p-4'}`}>
          <div className="flex items-center justify-between">
            <div>
              {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
              {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
            </div>
            {headerAction && <div>{headerAction}</div>}
          </div>
        </div>
      )}
      <div className={padding ? 'p-6' : ''}>
        {children}
      </div>
    </div>
  );
};

export default Card;
